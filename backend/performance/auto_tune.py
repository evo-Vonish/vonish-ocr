from dataclasses import asdict, dataclass


@dataclass
class RuntimePolicy:
    """后端真实执行策略。

    这里的并发数不是跑分上限，而是 OCR + DirectML + OpenCV 长时间批处理的安全值。
    """

    mode: str
    tier: str
    max_workers: int
    concurrency: int
    batch_size: int
    preprocess_workers: int
    intra_op_threads: int
    inter_op_threads: int
    use_iobinding: bool
    model_resident_strategy: str
    safe_vram_gb: float
    safe_memory_gb: float
    thermal_limit_c: int
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _gpu_tier(vram_gb: float, shared: bool) -> str:
    if shared or vram_gb < 4:
        return "D"
    if vram_gb >= 16:
        return "A"
    if vram_gb >= 10:
        return "B"
    if vram_gb >= 6:
        return "C"
    return "D"


def _mode_multiplier(mode: str) -> float:
    return {
        "auto": 1.0,
        "balanced": 1.0,
        "beast": 1.35,
        "eco": 0.55,
        "custom": 1.0,
    }.get(mode, 1.0)


def compute_runtime_policy(hardware: dict, mode: str = "balanced", overrides: dict | None = None) -> RuntimePolicy:
    """根据硬件探针计算保守策略。

    报告里的高并发伪代码不能直接照搬。OCR 预处理会产生瞬时内存和显存分配，
    因此这里优先保证 10-50 张批量任务稳定跑完，再给“野兽”模式有限放宽。
    """

    overrides = overrides or {}
    cpu = hardware.get("cpu") or {}
    mem = hardware.get("memory") or {}
    gpus = hardware.get("gpu") or hardware.get("gpus") or []
    gpu = gpus[0] if gpus else {}

    physical = int(cpu.get("physical_cores") or max(1, int(cpu.get("logical_cores") or 2) // 2))
    logical = int(cpu.get("logical_cores") or physical)
    total_mem = float(mem.get("total_gb") or 0)
    safe_mem = float(mem.get("safe_memory_gb") or 0.5)
    vram = float(gpu.get("vram_total_gb") or gpu.get("vram_dedicated_gb") or 0)
    shared = bool(gpu.get("shared_memory")) or gpu.get("vendor") in ("Apple", "Intel", "Unknown")
    tier = _gpu_tier(vram, shared)

    base_by_tier = {
        "A": {"concurrency": 4, "batch": 4, "resident": "all"},
        "B": {"concurrency": 3, "batch": 3, "resident": "fast_standard"},
        "C": {"concurrency": 2, "batch": 2, "resident": "fast_only"},
        "D": {"concurrency": 1, "batch": 1, "resident": "on_demand"},
    }[tier]

    multiplier = _mode_multiplier(mode)
    concurrency = _clamp(round(base_by_tier["concurrency"] * multiplier), 1, 6)
    batch_size = _clamp(round(base_by_tier["batch"] * multiplier), 1, 6)

    if total_mem and total_mem < 8:
        concurrency = min(concurrency, 1)
        batch_size = 1
    elif safe_mem and safe_mem < 4:
        concurrency = min(concurrency, 2)

    if shared:
        concurrency = min(concurrency, 1 if mode != "beast" else 2)
        batch_size = 1

    preprocess_workers = _clamp(physical // 4, 1, 4)
    if mode == "eco":
        preprocess_workers = 1

    intra = _clamp(physical - 2, 2, max(2, physical))
    if preprocess_workers + intra > logical:
        intra = _clamp(logical - preprocess_workers, 2, max(2, logical))

    if mode == "custom":
        concurrency = _clamp(overrides.get("concurrency", concurrency), 1, 8)
        batch_size = _clamp(overrides.get("batch_size", batch_size), 1, 8)
        preprocess_workers = _clamp(overrides.get("preprocess_workers", preprocess_workers), 1, max(1, logical))
        intra = _clamp(overrides.get("intra_op_threads", intra), 1, max(1, physical))

    max_workers = _clamp(concurrency, 1, 4)
    thermal_limit = 80 if hardware.get("is_laptop") else 85
    if mode == "eco":
        thermal_limit -= 5

    reason_bits = []
    if gpu:
        reason_bits.append(f"{gpu.get('name', 'GPU')} / {vram:.1f}GB VRAM")
    else:
        reason_bits.append("CPU only")
    reason_bits.append(f"{physical}P/{logical}T CPU")
    reason_bits.append(f"{safe_mem:.1f}GB safe memory")
    if shared:
        reason_bits.append("shared memory guard")

    return RuntimePolicy(
        mode=mode,
        tier=tier,
        max_workers=max_workers,
        concurrency=concurrency,
        batch_size=batch_size,
        preprocess_workers=preprocess_workers,
        intra_op_threads=intra,
        inter_op_threads=1,
        use_iobinding=bool(gpu and not shared and tier != "D"),
        model_resident_strategy=base_by_tier["resident"],
        safe_vram_gb=round(vram * (0.5 if shared else 0.7), 1) if vram else 0,
        safe_memory_gb=round(safe_mem, 1),
        thermal_limit_c=thermal_limit,
        reason=" / ".join(reason_bits),
    )


def profile_cards(hardware: dict, active_mode: str, overrides: dict | None = None) -> list[dict]:
    labels = {
        "auto": "自动",
        "beast": "野兽",
        "balanced": "均衡",
        "eco": "节能",
        "custom": "自定义",
    }
    cards = []
    for mode in ("auto", "beast", "balanced", "eco"):
        policy = compute_runtime_policy(hardware, mode, overrides)
        cards.append({
            "id": mode,
            "name": labels[mode],
            "active": mode == active_mode,
            "policy": policy.to_dict(),
        })
    return cards
