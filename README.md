# VonishOCR

本地优先的 OCR 桌面应用，定位类比 Ollama 但专注 OCR 领域。

## 核心特性

- **算力在本地**：OCR 推理完全在用户设备上完成，支持 DirectML GPU 加速
- **模型可管理**：支持多模型下载、切换、热加载、自动驱逐
- **场景自适应**：8 类场景自动识别（打印文档/手写笔记/截图/身份证/表格/户外照片/低质量扫描/试卷），匹配最佳预处理流程
- **AI 修复可选**：用户可自备 API Key（DeepSeek/OpenAI/Qwen），对低质量 OCR 结果进行后处理修正
- **批量处理**：支持单次最高 200 张图片的队列式处理，WebSocket 实时进度推送
- **功耗模式**：野兽/均衡/省电三档，适配不同使用场景

## 技术栈

- **桌面壳**：Tauri 2 / Rust
- **前端**：Vue 3 / Vite / Pinia
- **后端**：Python 3.12 / FastAPI / Uvicorn
- **OCR 引擎**：ONNXRuntime + rapidocr-onnxruntime（支持 DirectML GPU）
- **预处理**：OpenCV，场景自适应流水线

## 快速开始

```bash
# 安装依赖（PowerShell）
scripts\setup_dev.ps1

# 开发模式（热重载）
cargo tauri dev

# 后端独立测试
cd backend && python main.py

# 一键打包
python scripts/build.py
```

## 项目结构

```
VonishOCR
├── backend/              # Python FastAPI 后端
│   ├── api/              # HTTP / WebSocket 路由
│   ├── core/             # OCR 引擎管理器
│   ├── ai_refiner/       # AI 修复模块
│   ├── preprocess/       # 图像预处理流水线
│   ├── scene/            # 场景分类器
│   └── task_queue/       # 批量任务队列
├── src/                  # Vue3 前端
│   ├── components/       # UploadZone / ResultPanel / ConfigDrawer
│   ├── stores/           # Pinia Stores
│   └── api/              # Tauri IPC 封装
├── src-tauri/            # Rust Tauri 壳
├── models/               # ONNX 模型文件
├── scripts/              # 构建/安装脚本
└── logs/                 # 运行时日志
```

## 模型

| 模型 | 大小 | 语言 | 能力 |
|------|------|------|------|
| rapidocr-mobile-cn | ~22MB | 中英 | 文字识别 |
| cnocr-standard-cn | ~22MB | 中英 | 文字+表格 |
| paddleocr-vl-1.5 | ~1.8GB | 中英 | 文字+表格+公式（Phase 3） |

## Phase 2.3 功能

- **预处理流水线**：自动旋转 → 倾斜校正 → 去噪 → CLAHE 对比度增强 → 质量评估回退
- **场景分类**：传统 CV 规则分类器（<5ms），8 类场景自动识别
- **AI Refiner**：DeepSeek/OpenAI/Qwen 多提供商，低置信度自动触发
- **批量并发**：4-8 workers + asyncio.to_thread，200 张 36 秒
- **系统托盘**：关闭窗口不退出，托盘可恢复
- **结果导出**：TXT / JSON / Markdown + 剪贴板复制

## 系统要求

- Windows 10/11
- Python 3.12+
- Node.js 20+
- Rust 1.75+
- NVIDIA/AMD/Intel GPU（DirectML 支持）
