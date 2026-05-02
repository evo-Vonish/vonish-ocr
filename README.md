# VonishOCR

本地优先的 OCR 模型管理器，定位类比 Ollama 但专注 OCR 领域。

## 核心特性

- **算力在本地**：OCR 推理完全在用户设备上完成
- **模型可管理**：支持多模型下载、切换、热加载、自动驱逐
- **场景自适应**：自动识别输入图片类型，匹配最佳预处理流程和模型
- **AI 修复可选**：用户可自备 API Key，对低质量 OCR 结果进行后处理修正
- **批量处理**：支持单次最高 200 张图片的队列式处理

## 技术栈

- **后端**：Python 3.11+ / FastAPI / Uvicorn
- **前端**：Vue 3 / Vite / Pinia
- **模型运行时**：ONNXRuntime / PaddlePaddle

## 快速开始

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 启动后端
python main.py

# 安装前端依赖并启动
cd frontend
npm install
npm run dev
```

或在 Windows 下直接运行：

```bash
scripts\start_dev.bat
```

- 后端地址：http://localhost:8000
- 前端地址：http://localhost:5173

## 项目结构

```
VonishOCR
├── backend/          # Python FastAPI 后端 + OCR 核心
├── frontend/         # Vue3 + Vite 前端
├── scripts/          # 启动/打包脚本
├── tests/            # 测试目录
├── docs/             # 项目文档
└── resources/        # 打包资源
```

## Phase 0 目标

骨架跑通，前后端能启动，模块间能导入，API 接口能访问。
