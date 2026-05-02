#!/usr/bin/env python3
"""
VonishOCR 一键打包脚本

执行流程：
1. 检查环境（Rust、Node、Python、PyInstaller）
2. 前端构建：npm install && npm run build
3. Python 打包：pyinstaller backend/main.py ...
4. Tauri 构建：cargo tauri build
5. 收集输出

用法：
    python scripts/build.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def _find_npm():
    """动态查找 npm 路径。"""
    # 先尝试 PATH 中的 npm
    npm = shutil.which("npm")
    if npm:
        return npm
    # Windows 常见安装路径
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs" / "npm.cmd",
        Path(os.environ.get("LOCALAPPDATA", "")) / "nodejs" / "npm.cmd",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError("未找到 npm，请安装 Node.js 并确保 PATH 中包含 npm")


NPM_CMD = _find_npm()


def run(cmd, cwd=None, check=True):
    """执行命令并打印输出"""
    print(f"\n>>> {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd, cwd=cwd or PROJECT_ROOT, check=check, capture_output=False, text=True
    )
    return result


def check_env():
    """检查必要工具是否安装"""
    print("=" * 50)
    print("检查构建环境...")
    print("=" * 50)

    tools = [
        ("rustc", ["rustc", "--version"]),
        ("cargo", ["cargo", "--version"]),
        ("node", ["node", "--version"]),
        ("npm", [NPM_CMD, "--version"]),
        ("python", [sys.executable, "--version"]),
    ]

    missing = []
    for name, cmd in tools:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"  OK  {name}: {result.stdout.strip() or result.stderr.strip()}")
            else:
                missing.append(name)
                print(f"  MISSING {name}")
        except FileNotFoundError:
            missing.append(name)
            print(f"  MISSING {name}")

    # 检查 PyInstaller
    try:
        import PyInstaller

        print("  OK  pyinstaller: 已安装")
    except ImportError:
        print("  MISSING pyinstaller")
        print("  安装命令: pip install pyinstaller")
        missing.append("pyinstaller")

    # 检查 Tauri CLI
    try:
        result = subprocess.run(
            ["cargo", "tauri", "--version"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print(f"  OK  tauri-cli: {result.stdout.strip()}")
        else:
            print("  MISSING tauri-cli")
            print("  安装命令: cargo install tauri-cli")
            missing.append("tauri-cli")
    except FileNotFoundError:
        missing.append("tauri-cli")

    if missing:
        print(f"\n缺失工具: {', '.join(missing)}")
        print("请运行 scripts/setup_dev.ps1 安装环境")
        sys.exit(1)

    print("\n环境检查通过！")


def build_frontend():
    """构建前端"""
    print("\n" + "=" * 50)
    print("步骤 1: 构建前端")
    print("=" * 50)
    run([NPM_CMD, "install"])
    run([NPM_CMD, "run", "build"])


def build_python():
    """打包 Python 后端"""
    print("\n" + "=" * 50)
    print("步骤 2: 打包 Python 后端")
    print("=" * 50)

    backend_dir = PROJECT_ROOT / "backend"
    output_dir = PROJECT_ROOT / "backend_dist"

    # 清理旧输出
    if output_dir.exists():
        shutil.rmtree(output_dir)

    build_dir = PROJECT_ROOT / "build"
    build_dir.mkdir(exist_ok=True)

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name",
            "vonish_ocr_backend",
            "--onedir",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(output_dir),
            "--workpath",
            str(build_dir / "pyinstaller"),
            "--specpath",
            str(build_dir),
            "--hidden-import",
            "fastapi",
            "--hidden-import",
            "uvicorn",
            "--hidden-import",
            "pydantic",
            "--hidden-import",
            "pydantic_settings",
            "--add-data",
            f"{backend_dir / 'models' / 'manifest.json'};models",
            str(backend_dir / "main.py"),
        ]
    )


def build_tauri():
    """构建 Tauri 桌面应用"""
    print("\n" + "=" * 50)
    print("步骤 3: 构建 Tauri 桌面应用")
    print("=" * 50)

    run(["cargo", "tauri", "build"], cwd=PROJECT_ROOT / "src-tauri")


def collect_outputs():
    """收集构建产物"""
    print("\n" + "=" * 50)
    print("步骤 4: 收集构建产物")
    print("=" * 50)

    bundle_dir = PROJECT_ROOT / "src-tauri" / "target" / "release" / "bundle"

    outputs = []

    # MSI
    msi_dir = bundle_dir / "msi"
    if msi_dir.exists():
        for f in msi_dir.glob("*.msi"):
            outputs.append(f)

    # NSIS
    nsis_dir = bundle_dir / "nsis"
    if nsis_dir.exists():
        for f in nsis_dir.glob("*.exe"):
            if "setup" in f.name.lower():
                outputs.append(f)

    # 便携版
    portable = (
        PROJECT_ROOT / "src-tauri" / "target" / "release" / "vonish-ocr.exe"
    )
    if portable.exists():
        outputs.append(portable)

    if outputs:
        print("\n构建产物:")
        for o in outputs:
            size_mb = o.stat().st_size / (1024 * 1024)
            print(f"  {o} ({size_mb:.1f} MB)")
    else:
        print("未找到构建产物")

    return outputs


def main():
    check_env()
    build_frontend()
    build_python()
    build_tauri()
    collect_outputs()
    print("\n" + "=" * 50)
    print("打包完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
