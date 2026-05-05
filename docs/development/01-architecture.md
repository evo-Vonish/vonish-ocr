# 技术架构

VonishOCR 采用分层架构，桌面壳、前端界面、后端引擎各司其职，通过标准化接口通信。

## 架构总览

```
+-----------------------------------------+
|              前端界面层                   |
|     Vue 3.4 + Vite 5.4 + Pinia           |
|     Tailwind CSS + CSS Variables         |
+-----------------------------------------+
|              桌面壳层                     |
|     Tauri v2 + Rust                      |
|     系统托盘 / 窗口管理 / Python Sidecar |
+-----------------------------------------+
|              后端引擎层                   |
|     Python 3.12 + FastAPI + Uvicorn      |
|     ONNXRuntime (DirectML)               |
+-----------------------------------------+
|              模型层                       |
|     rapidocr / cnocr / paddleocr         |
|     ONNX 模型文件                        |
+-----------------------------------------+
```

## 前端：Vue 3 + Tauri

前端使用 Vue 3 组合式 API 与 Pinia 状态管理，构建响应式的暗色"证据桌"界面。

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4 | 组件框架、响应式系统 |
| Vite | 5.4 | 构建工具、HMR |
| Pinia | 2.x | 全局状态管理（taskStore、configStore）|
| Tailwind CSS | 3.x | 原子化样式 |

前端代码位于 `src/` 目录，主要组件包括：

- `App.vue`：五区布局（topbar / left-rail / workbench / right-review / bottombar）
- `UploadZone.vue`：上传拖拽区 + 批量队列
- `ResultPanel.vue`：三栏结果展示
- `ConfigDrawer.vue`：配置抽屉
- `AIProviderCenter.vue`：AI 方案管理
- `ToastStack.vue`：全局 Toast 容器
- `DialogSystem.vue`：模态弹窗系统

## 桌面壳：Tauri v2 + Rust

Tauri 负责将前端打包为桌面应用，同时提供系统级能力：

| 能力 | 实现 |
|------|------|
| 窗口管理 | Tauri 窗口 API |
| 系统托盘 | `tauri-plugin-notification` |
| 文件系统访问 | Tauri FS API |
| Python Sidecar | `std::process::Command` 启动 Python 后端 |
| IPC 通信 | Tauri Command（Rust <-> JS）|

Rust 代码位于 `src-tauri/src/` 目录：

- `main.rs`：Tauri 入口、IPC 命令注册、Tray 初始化、Sidecar 管理
- `Cargo.toml`：依赖配置（tauri v2 + notification/shell/opener 插件）

## 后端：Python FastAPI

Python 后端是 OCR 能力的实际执行者，以 Sidecar 形式由 Tauri 启动。

| 模块 | 文件 | 职责 |
|------|------|------|
| 入口 | `backend/main.py` | FastAPI 生命周期、队列启动 |
| 路由 | `backend/api/routes.py` | HTTP / WebSocket 端点 |
| OCR 引擎 | `backend/core/ocr_engine.py` | ONNXRuntime 推理管理 |
| AI 精修 | `backend/ai_refiner/refiner.py` | LLM 调用、failover、SSE |
| 预处理 | `backend/preprocess/pipeline.py` | 图像预处理 10 步管线 |
| 场景分类 | `backend/scene/classifier.py` | 8 类规则分类器 |
| 任务队列 | `backend/task_queue/local_queue.py` | 批量并发队列 |
| 配置 | `backend/config/settings.py` | UserConfig / AIScheme |

## 通信层

前端与后端之间存在两条通信路径：

### Tauri IPC（Rust 桥接）

```javascript
// 前端调用 Rust IPC
const result = await invoke('ocr_recognize', {
  imageBase64: '...',
  options: { scene: 'print' }
})
```

```rust
// Rust 处理 IPC，转发至 Python
#[tauri::command]
fn ocr_recognize(image_base64: String, options: String) -> Result<String, String> {
    // 通过 HTTP 转发给 localhost:8000
}
```

### 直接 HTTP（开发模式 / 本地 API）

开发模式下，前端直接向后端的 `localhost:8000` 发送 HTTP 请求，绕过 Tauri IPC：

```javascript
const res = await fetch('http://localhost:8000/v1/ocr', {
  method: 'POST',
  body: formData
})
```

生产打包后，前端通过 Tauri IPC 调用 Rust，Rust 再转发给 Python。这种双层设计让开发模式可以独立调试前端与后端，无需启动 Tauri。

## 数据流

一次完整的单图识别数据流：

```
用户拖入图片
  -> 前端读取文件为 base64
  -> 调用 ocrRecognize()（IPC 或 HTTP）
  -> Rust 转发至 Python FastAPI
  -> 场景分类器判断类型（<5ms）
  -> 预处理管线执行（旋转/去斜/降噪/增强）
  -> OCR 引擎推理（ONNXRuntime）
  -> 返回原始 OCR 结果
  -> 如开启 AI 精修：调用 Refiner（SSE 流式输出）
  -> 前端接收结果，写入 taskStore
  -> ResultPanel 展示三栏内容
```

---

> 分层架构的优势在于隔离与替换。前端可以独立迭代界面，后端可以独立升级模型，桌面壳负责将两者粘合。未来若要将后端迁移至 Rust 原生实现，只需替换 Python Sidecar 层，前端与 Tauri 层完全无感。
