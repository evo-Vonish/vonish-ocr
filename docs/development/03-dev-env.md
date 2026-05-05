# 本地开发环境

以下是从零开始搭建 VonishOCR 开发环境的完整流程。

## 环境要求

| 工具 | 最低版本 | 推荐版本 | 验证命令 |
|------|---------|---------|---------|
| Node.js | 20 | 20 LTS | `node --version` |
| Python | 3.12 | 3.12 | `python --version` |
| Rust | 1.75 | 1.78+ | `rustc --version` |
| Git | 2.40 | 最新 | `git --version` |

## 第一步：Clone 仓库

```bash
git clone https://github.com/evo-Vonish/vonish-ocr.git
cd vonish-ocr
```

## 第二步：安装前端依赖

```bash
npm install
```

或使用 PowerShell 一键脚本（Windows）：

```powershell
scripts/setup_dev.ps1
```

脚本会自动：
- 检查 Node.js 版本
- 安装 npm 依赖
- 创建本地开发配置文件

## 第三步：安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

核心 Python 依赖包括：

| 包 | 用途 |
|----|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| onnxruntime-directml | ONNX 推理（DirectML 加速）|
| opencv-python | 图像预处理 |
| numpy | 数值计算 |
| Pillow | 图像格式转换 |
| psutil | 硬件监控 |
| nvidia-ml-py | NVIDIA GPU 监控（如适用）|

## 第四步：安装 Rust 依赖

```bash
cd src-tauri
cargo fetch
```

Tauri v2 的依赖会自动解析并下载。

## 第五步：下载模型

模型文件需手动放置到 `models/` 目录：

```
models/
├── rapidocr-mobile-cn.onnx      # 22MB，极速模型
├── cnocr-standard-cn.onnx       # 80MB，标准模型
└── manifest.json                # 模型元数据
```

模型下载地址：
- rapidocr-mobile-cn：[RapidOCR Releases](https://github.com/RapidAI/RapidOCR/releases)
- cnocr-standard-cn：[CnOCR Releases](https://github.com/breezedeus/cnocr/releases)

模型路径可在 `config.json` 中修改，支持绝对路径（如 `F:/VonishOCR/models/`）。

## 第六步：启动开发环境

**重要**：不要使用 `cargo tauri dev`，因为它会在 120 秒超时后强制杀掉前端进程。

推荐方式：分终端启动。

### 终端 1：Vite 前端

```bash
# 在项目根目录
node node_modules/vite/bin/vite.js
```

前端服务启动于 `http://localhost:1420`。

### 终端 2：Tauri Rust

```bash
cd src-tauri
cargo run
```

Rust 编译首次可能耗时 3-5 分钟，后续增量编译通常在 10 秒内。

### 终端 3：Python 后端（独立调试）

```bash
cd backend
python main.py
```

后端服务启动于 `http://localhost:8000`。独立调试时前端直接访问此地址，不经过 Tauri IPC。

## 开发环境常见问题

### PowerShell 执行策略阻止

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Vite 端口占用

```powershell
# 查找并 kill 占用 1420 的进程
Get-NetTCPConnection -LocalPort 1420 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
```

### Vite HMR 缓存异常

```bash
rm -rf node_modules/.vite
# 重新启动 Vite
```

### Python 后端日志

后端日志输出至 `logs/backend.log`，按 10MB 大小轮转，保留最近 5 个文件。

---

> 开发环境的分终端启动看似繁琐，实则带来了最大的调试灵活性。你可以独立重启前端而不影响后端推理状态，也可以独立重启后端而不丢失前端的文件选择状态。
