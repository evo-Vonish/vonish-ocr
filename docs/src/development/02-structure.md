# 目录结构

VonishOCR 项目的完整目录树及各目录职责说明。

```
VonishOCR/
├── backend/                    # Python FastAPI 后端
│   ├── api/
│   │   └── routes.py           # HTTP / WebSocket 路由定义
│   ├── core/
│   │   └── ocr_engine.py       # ONNXRuntime OCR 引擎管理器
│   ├── ai_refiner/
│   │   ├── refiner.py          # AIRefiner 类（prompt、API 调用、failover）
│   │   └── __init__.py         # 模块导出
│   ├── config/
│   │   └── settings.py         # UserConfig / AIScheme / ConfigManager
│   ├── preprocess/
│   │   └── pipeline.py         # 图像预处理 10 步管线
│   ├── scene/
│   │   └── classifier.py       # 8 类规则场景分类器
│   ├── task_queue/
│   │   └── local_queue.py      # 批量并发队列（Semaphore 控制）
│   └── main.py                 # FastAPI 入口、生命周期、队列启动
│
├── src/                        # Vue3 前端
│   ├── components/             # Vue 单文件组件
│   │   ├── UploadZone.vue      # 上传拖拽区 + 批量队列 UI
│   │   ├── ResultPanel.vue     # 三栏结果展示（raw/polished/diff）
│   │   ├── ConfigDrawer.vue    # 配置抽屉（设置面板）
│   │   ├── AIProviderCenter.vue # AI 方案管理界面
│   │   ├── ToastStack.vue      # 全局 Toast 容器
│   │   └── DialogSystem.vue    # 模态弹窗系统
│   ├── stores/                 # Pinia 状态管理
│   │   ├── taskStore.js        # 任务状态中心（single source of truth）
│   │   └── configStore.js      # 配置持久化
│   ├── composables/            # Vue 组合式函数
│   │   ├── useAIStream.js      # AI SSE 流式处理封装
│   │   ├── useToast.js         # Toast API
│   │   ├── useDialog.js        # Dialog API
│   │   └── useNotify.js        # Windows 原生通知封装
│   ├── api/                    # 后端通信封装
│   │   └── tauri_ipc.js        # Tauri IPC + HTTP 桥接
│   ├── App.vue                 # 主布局（五区架构）
│   └── main.js                 # Vue 入口、全局错误拦截、Pinia 注册
│
├── src-tauri/                  # Rust Tauri 桌面壳
│   ├── src/
│   │   └── main.rs             # Tauri 入口、IPC 命令、Python Sidecar、Tray
│   ├── Cargo.toml              # Rust 依赖（tauri v2 + plugins）
│   └── capabilities/
│       └── default.json        # Tauri 权限配置
│
├── models/                     # ONNX 模型文件
│   ├── rapidocr-mobile-cn.onnx
│   ├── cnocr-standard-cn.onnx
│   └── manifest.json           # 模型元数据、版本、大小、适用场景
│
├── docs/                       # VitePress 文档站（本工程）
│   ├── .vitepress/             # VitePress 配置与主题
│   ├── src/                    # Markdown 文档源文件
│   └── index.md                # 首页
│
├── scripts/                    # 构建与安装脚本
│   ├── setup_dev.ps1           # 开发环境一键安装（PowerShell）
│   └── build.py                # 一键打包脚本
│
├── public/                     # 静态资源
│   ├── logo.svg                # 应用 Logo
│   └── favicon.ico             # 站点图标
│
├── build/                      # 构建输出（.msi/.dmg/.AppImage）
│
├── logs/                       # 运行时日志
│   └── backend.log             # Python 后端日志
│
├── config.json                 # 用户配置文件（前端 + 后端共享）
├── package.json                # Node.js 依赖
├── vite.config.js              # Vite 配置
├── index.html                  # 前端入口 HTML
├── .gitignore                  # Git 忽略规则
├── README.md                   # 项目说明
├── HANDOVER.md                 # 项目转交书
└── BUGS.md                     # Bug 清单
```

## 关键路径约定

| 路径 | 用途 | 说明 |
|------|------|------|
| `backend/` | Python 代码 | 后端独立运行时的工作目录 |
| `src/` | 前端源码 | Vite 的源码目录，构建后输出至 `dist/` |
| `src-tauri/` | Rust 源码 | Tauri CLI 会自动识别此目录 |
| `models/` | 模型文件 | 可在设置中修改路径，默认与项目同级 |
| `logs/` | 日志 | 后端自动创建，按日期轮转 |

---

> 目录结构的组织原则是「按职责分层，不按技术分层」。`backend/` 不是 `python/`，`src/` 不是 `frontend/`，因为技术栈可能变化（如后端未来可能用 Rust 重写），但职责边界是稳定的。
