import os
import platform
import shutil
import subprocess
from pathlib import Path


def _round_gb(value: float) -> float:
    return round(float(value), 1)


def detect_cpu() -> dict:
    """Best-effort CPU snapshot.

    All optional libraries are guarded because the sidecar must still start on
    machines without psutil or py-cpuinfo.
    """
    logical = os.cpu_count() or 1
    physical = max(1, logical // 2)
    brand = platform.processor() or platform.machine() or "CPU"
    freq_mhz = 0
    flags: list[str] = []

    try:
      import psutil

      physical = psutil.cpu_count(logical=False) or physical
      logical = psutil.cpu_count(logical=True) or logical
      freq = psutil.cpu_freq()
      if freq:
          freq_mhz = round(freq.current or freq.max or 0, 1)
    except Exception:
      pass

    try:
      from cpuinfo import get_cpu_info

      info = get_cpu_info()
      brand = info.get("brand_raw") or brand
      flags = [str(flag).lower() for flag in info.get("flags", [])]
    except Exception:
      pass

    machine = platform.machine()
    if machine in ("AMD64", "x86_64") and os.name == "nt":
        proc_id = os.environ.get("PROCESSOR_IDENTIFIER", "")
        if "ARMv8" in proc_id or "ARM64" in proc_id:
            machine = "ARM64"

    return {
        "brand": brand,
        "arch": machine,
        "physical_cores": physical,
        "logical_cores": logical,
        "hyperthreading": logical > physical,
        "frequency_mhz": freq_mhz,
        "avx2": "avx2" in flags,
        "avx512": "avx512f" in flags,
        "neon": "neon" in flags or "asimd" in flags,
        "is_apple_silicon": platform.system() == "Darwin" and machine == "arm64",
    }


def detect_memory() -> dict:
    """Memory snapshot plus a conservative safe allocation ceiling."""
    total_gb = 0.0
    available_gb = 0.0
    percent = 0.0

    try:
      import psutil

      mem = psutil.virtual_memory()
      total_gb = mem.total / (1024 ** 3)
      available_gb = mem.available / (1024 ** 3)
      percent = float(mem.percent)
    except Exception:
      pass

    if total_gb >= 8:
        safe_gb = max(0.5, available_gb * 0.75 - 2)
    else:
        safe_gb = max(0.5, available_gb * 0.5 - 1)

    return {
        "total_gb": _round_gb(total_gb),
        "available_gb": _round_gb(available_gb),
        "safe_memory_gb": _round_gb(safe_gb),
        "percent": round(percent, 1),
        "low_memory": bool(total_gb and total_gb < 8),
    }


def _num(value) -> float:
    try:
        return float(str(value).replace("W", "").replace("%", "").strip())
    except Exception:
        return 0.0


def _detect_nvidia() -> list[dict]:
    query = "name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw,fan.speed"
    try:
        completed = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return []

    rows = []
    for index, line in enumerate((completed.stdout or "").splitlines()):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        rows.append({
            "vendor": "NVIDIA",
            "name": parts[0],
            "vram_total_gb": round(_num(parts[1]) / 1024, 1),
            "vram_used_gb": round(_num(parts[2]) / 1024, 1),
            "util": round(_num(parts[3]), 1),
            "temp": round(_num(parts[4]), 1),
            "power": round(_num(parts[5]), 1),
            "fan": round(_num(parts[6]) * 40),
            "shared_memory": False,
            "index": index,
        })
    return rows


def _detect_windows_display() -> list[dict]:
    if os.name != "nt":
        return []
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        import json

        raw = json.loads(completed.stdout or "[]")
        items = raw if isinstance(raw, list) else [raw]
    except Exception:
        return []

    gpus = []
    for item in items:
        name = str(item.get("Name") or "")
        if not name or "Microsoft" in name:
            continue
        ram = item.get("AdapterRAM") or 0
        vram = round(max(0, float(ram)) / (1024 ** 3), 1) if ram else 0
        vendor = "Intel" if "Intel" in name else "AMD" if ("AMD" in name or "Radeon" in name) else "Unknown"
        gpus.append({
            "vendor": vendor,
            "name": name,
            "vram_total_gb": vram,
            "vram_used_gb": 0,
            "util": 0,
            "temp": 0,
            "power": 0,
            "fan": 0,
            "shared_memory": vendor in ("Intel", "Unknown") or vram < 4,
            "index": len(gpus),
        })
    return gpus


def detect_gpu() -> list[dict]:
    gpus = _detect_nvidia()
    if not gpus:
        gpus = _detect_windows_display()
    if not gpus and platform.system() == "Darwin" and platform.machine() == "arm64":
        mem = detect_memory()
        gpus = [{
            "vendor": "Apple",
            "name": "Apple Silicon GPU",
            "vram_total_gb": mem["total_gb"],
            "vram_used_gb": 0,
            "util": 0,
            "temp": 0,
            "power": 0,
            "fan": 0,
            "shared_memory": True,
            "index": 0,
        }]
    return gpus


def detect_temperatures(gpus: list[dict] | None = None) -> dict:
    cpu_temp = None
    gpu_temp = None
    if gpus:
        gpu_temp = gpus[0].get("temp") or None
    try:
        import psutil

        temps = getattr(psutil, "sensors_temperatures", lambda: {})()
        for name, entries in temps.items():
            if name in ("coretemp", "k10temp") and entries:
                cpu_temp = entries[0].current
                break
    except Exception:
        pass
    return {"cpu": cpu_temp, "gpu": gpu_temp}


def full_hardware_probe(root: Path | None = None, models_dir: Path | None = None) -> dict:
    root = root or Path.cwd()
    models_dir = models_dir or root / "models"
    cpu = detect_cpu()
    memory = detect_memory()
    gpu = detect_gpu()
    temps = detect_temperatures(gpu)
    disk = shutil.disk_usage(root)
    return {
        "cpu": cpu,
        "gpu": gpu,
        "memory": memory,
        "temperatures": temps,
        "platform": platform.system(),
        "platform_release": platform.release(),
        "disk": {
            "free_gb": round(disk.free / (1024 ** 3), 1),
            "total_gb": round(disk.total / (1024 ** 3), 1),
            "model_cache_gb": round(_dir_size(models_dir) / (1024 ** 3), 2),
        },
        "is_laptop": _is_laptop(),
    }


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def _is_laptop() -> bool:
    try:
        import psutil

        return psutil.sensors_battery() is not None
    except Exception:
        return False

