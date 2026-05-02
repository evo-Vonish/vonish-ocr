# VonishOCR 开发环境一键安装脚本 (Windows PowerShell)
# 安装：Rust、Tauri CLI、Node 依赖、Python 依赖

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$msg)
    Write-Host "`n$('='*50)" -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor Cyan
    Write-Host "$('='*50)" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$cmd)
    try { $null = Get-Command $cmd -ErrorAction Stop; return $true } catch { return $false }
}

# 1. Rust
Write-Step "检查 Rust..."
if (Test-Command "rustc") {
    Write-Host "OK Rust 已安装: $(rustc --version)" -ForegroundColor Green
} else {
    Write-Host "正在安装 Rust..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://win.rustup.rs/x86_64" -OutFile "$env:TEMP\rustup-init.exe"
    & "$env:TEMP\rustup-init.exe" -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path
    Write-Host "OK Rust 安装完成" -ForegroundColor Green
}

# 2. Tauri CLI
Write-Step "检查 Tauri CLI..."
if (Test-Command "cargo") {
    $tauriVersion = cargo tauri --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Tauri CLI 已安装: $tauriVersion" -ForegroundColor Green
    } else {
        Write-Host "正在安装 Tauri CLI..." -ForegroundColor Yellow
        cargo install tauri-cli
        Write-Host "OK Tauri CLI 安装完成" -ForegroundColor Green
    }
} else {
    Write-Host "MISSING cargo 未找到，请确保 Rust 已正确安装" -ForegroundColor Red
}

# 3. Node.js
Write-Step "检查 Node.js..."
if (Test-Command "node") {
    Write-Host "OK Node.js 已安装: $(node --version)" -ForegroundColor Green
} else {
    Write-Host "MISSING 请从 https://nodejs.org/ 下载并安装 Node.js 18+" -ForegroundColor Red
}

# 4. Python 依赖
Write-Step "检查 Python 依赖..."
& python -m pip install --upgrade pip
& python -m pip install -r backend\requirements.txt
& python -m pip install pyinstaller
Write-Host "OK Python 依赖安装完成" -ForegroundColor Green

# 5. Node 依赖
Write-Step "安装 Node 依赖..."
& npm install
Write-Host "OK Node 依赖安装完成" -ForegroundColor Green

Write-Step "开发环境准备完成！"
Write-Host "启动开发服务器: cargo tauri dev" -ForegroundColor Green
Write-Host "或运行开发模式: npm run dev  +  python backend/main.py" -ForegroundColor Green
