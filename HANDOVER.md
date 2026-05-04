# VonishOCR 项目转交书 & Bug 清单

> 生成时间：2026-05-05
> 最后操作：AI Refiner 调试中（Python 进程已死，需重启 Tauri）

---

## 一、项目概况

**VonishOCR** — 本地优先的 OCR 识别工具，Tauri + Vue3 + Python FastAPI 架构。

| 层级 | 技术栈 |
|------|--------|
| 前端 | Vue 3.4 + Vite 5.4 + Pinia + CSS Variables（暗色"证据桌"主题） |
| 桌面壳 | Tauri v2 + Rust（系统托盘、窗口管理、Python Sidecar） |
| 后端 | Python 3.12 + FastAPI + OpenCV + ONNX Runtime (DirectML) |
| OCR 引擎 | RapidOCR Mobile / CnOCR（~21MB ONNX 模型） |
| AI 修复 | DeepSeek / OpenAI / Qwen / Custom（OpenAI 兼容 API） |

---

## 二、已完成功能清单

### 核心 OCR
- [x] 单图 OCR（`POST /v1/ocr`）
- [x] 批量 OCR（`POST /v1/ocr/batch/json`，base64 列表，最大 500MB）
- [x] 自动场景分类（8 类 rule-based：打印文档、手写笔记、截屏、身份证、表格、户外照片、低质量扫描、试卷）
- [x] 预处理流水线（10 步：自动旋转、去斜、降噪、对比度增强、锐化、透视矫正等）
- [x] DirectML GPU 加速（RTX 5060，ONNX Runtime EP）
- [x] 批量队列（LocalQueue，4 workers，concurrency=3， Semaphore 控制）
- [x] WebSocket 实时进度推送

### AI 修复（Refiner）
- [x] 自动/手动触发 AI 修复
- [x] 多 Provider Failover（DeepSeek → OpenAI → Qwen ...）
- [x] SSE 流式输出（手动"重新精修"）
- [x] Diff / Uncertain 标记
- [x] AI Provider Center（方案管理、权重、加密存储 API Key）

### UI/UX
- [x] 暗色"证据桌"主题 + 4 套主题切换（dark/light/mono/hc）
- [x] 全局 Toast 通知系统（右上角滑入，4 种类型）
- [x] 模态 Dialog 系统（alert/confirm）
- [x] 配置抽屉（ConfigDrawer）
- [x] 系统托盘（关闭到托盘、托盘菜单）
- [x] 导出：TXT / JSON / Markdown / 剪贴板
- [x] ResultPanel（原始/精修/Diff 三标签、错误详情、复制错误信息）
- [x] 批量进度条 + 实时速度显示
- [x] 全局错误拦截（Vue errorHandler + window.onerror + unhandledrejection）

### Windows 原生通知
- [x] tauri-plugin-notification 已安装并注册
- [x] `useNotify.js` 封装（仅窗口最小化时触发）
- [x] ConfigDrawer 添加通知开关
- [x] UploadZone 集成（批量完成/失败时通知）
- [ ] **未验证**：用户已搁置

---

## 三、已修复的 Bug（历史记录）

| # | Bug | 修复方式 |
|---|-----|----------|
| 1 | `logging.handlers` import 缺失导致 Python sidecar 崩溃 | 添加 import |
| 2 | Tray icon `.unwrap()` panic（dev 模式） | `if let Some(icon)` 安全处理 |
| 3 | Vite dev server 120s 超时 kill | 分离 Vite + `cargo run` |
| 4 | ConfigDrawer `ref is not defined` | import 中添加 `ref` |
| 5 | IPC 返回 JSON string 而非 object | `_parseJson()` 统一解析 |
| 6 | Batch results 未写入 Pinia | 新增 `GET /v1/ocr/batch/{id}/results` + 前端轮询 |
| 7 | 50 图 batch 50MB 限制 | `MAX_BATCH_SIZE` 提至 500MB，前端 >20 图自动分 chunk |
| 8 | Failed tasks 不可删除 | `clearCompleted()` 包含 `failed` 状态 |
| 9 | Progress bar 消失 | timeout 60s→300s，延迟 3s 隐藏 |
| 10 | 没有 error popups | 全局 `useToast` + `ToastStack` + Vue errorHandler |
| 11 | ResultPanel 空白 | 统一 id 系统 + `currentTaskId` computed + localStorage 持久化 |
| 12 | Error card 缺乏 detail | 展开式错误卡片 + "复制给开发者" |
| 13 | `coro.send(None)` hack | 移除，`asyncio.run()` 线程循环消除 |
| 14 | Toast 没反应 | `ToastStack` 未挂载到 `App.vue` |
| 15 | 5 处原生 `alert()` | 全部替换为 `showToast()` / `vAlert()` |

---

## 四、当前活跃 Bug（按优先级）

### 🔴 P0 - AI Refiner JSON 解析失败（阻塞功能）

**现象**
- 自动 AI 修复时显示：`自动修复出错：deepseek: Unterminated string starting at: line 2 column 15 (char 16)`
- 手动"重新精修"时显示：`AI 修复失败：Failed to fetch`

**根因分析**
1. **JSON 解析问题**：LLM 返回的内容不是严格 JSON。可能原因：
   - 返回了 markdown 代码块包裹的 JSON（```json\n{...}\n```）
   - JSON 被 `max_tokens=4096` 截断
   - LLM 没理解 prompt，返回了纯文本或部分文本
2. **Failed to fetch**：Python sidecar 进程被杀死后未重启，后端无响应

**已尝试的修复**
- `backend/ai_refiner/refiner.py` 的 `_call_scheme`：
  - 添加了 markdown 代码块去除逻辑
  - `json.loads` 失败时抛出更清晰的错误
  - 超时从 30s 提升到 60s
- `refine_stream`：先 yield "start" 事件，再调 API
- 添加了后端调试日志（`AI refine_stream 开始`、`AI _call_scheme` 等）

**待验证**
- Python 进程当前已死，需重启 Tauri 加载最新代码
- 用户需确认 `config.json` 中 `ai.enabled: true` 且 API Key 有效

**建议的后续修复**
- 若 LLM 仍不返回严格 JSON，考虑：
  - 去掉 `response_format: {"type": "json_object"}`，改用纯文本 prompt + 后处理正则提取 JSON
  - 或增加 `max_tokens` 到 8192
  - 或在 prompt 中更明确地强调"不要 markdown 代码块"
- 给 `_call_scheme` 增加重试机制（遇到格式错误时重试 1 次）

---

### 🟡 P1 - AI 修复配置未启用（用户操作层面）

**现象**
- `config.json` 中：`ai.enabled: false`，`ai.api_key: null`
- 用户说"已添加并选中 API 方案"，但 `config.json` 中仍只有 `default-deepseek`，且 `key_saved: false`

**根因**
- AI 修复总开关未勾选
- 或 API Key 未正确保存到 SecureKeyStore

**解决方案**
1. 配置抽屉 → AI 修复 → 勾选「启用 AI 修复」
2. 输入 API Key（DeepSeek 以 `sk-` 开头）
3. 点击保存
4. AI Provider Center 中创建新方案并确保保存成功

---

### 🟡 P2 - 批量任务无 AI Refiner（功能缺失）

**现象**
- `main.py` 的 `recognize_sync_wrapper`（批量队列同步处理）中**完全没有 AI Refiner 后处理**
- 只有 `routes.py` 的 `ocr_single`（单图路由）有 AI Refiner

**代码位置**
- `backend/main.py` 第 129-183 行

**修复建议**
- 在 `recognize_sync_wrapper` 的末尾，参考 `ocr_single` 的 AI Refiner 逻辑，添加后处理
- 注意：批量任务逐图调用 LLM 会极大增加耗时和 API 费用，需评估是否添加开关

---

### 🟡 P3 - GPU 内存峰值（已缓解，可能需进一步调优）

**现象**
- RTX 5060 8GB 显存，峰值 15GB（ shared memory 占用系统内存）

**已做缓解**
- concurrency 从 8 降到 3
- 添加 `gc.collect()`

**建议**
- 如果仍出现 OOM，进一步降到 concurrency=1 或 2
- 或添加显存监控，动态调整 concurrency

---

### 🟢 P4 - Windows 原生通知（已搁置）

**状态**
- 代码已完成（`tauri-plugin-notification` + `useNotify.js` + ConfigDrawer 开关 + UploadZone 集成）
- 用户说"先晾一晾"
- 未实际验证是否正常工作

**已知限制**
- 仅窗口最小化时触发（设计如此）
- 需用户授予 Windows 通知权限

---

### 🟢 P5 - Vite 端口占用（开发环境问题）

**现象**
- 重启 Vite 时频繁遇到 `Port 1420 is already in use`

**原因**
- 之前的 node 进程未正确退出，持续占用端口

**Workaround**
```powershell
# 查找并 kill 占用 1420 的进程
Get-NetTCPConnection -LocalPort 1420 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
# 或简单粗暴
Get-Process -Name node | Stop-Process -Force
```

**建议**
- 开发脚本中添加 `--port 0` 让 Vite 自动选择可用端口（但 Tauri devUrl 需同步）

---

### 🟢 P6 - PaddleOCR 1.8GB 模型不可用（设计限制）

**现象**
- `paddleocr-vl-1.5` 模型文件是 HuggingFace Transformers 格式（safetensors），约 1.8GB
- 当前 `ONNXOCREngine` 只接受 ONNX 格式

**状态**
- 已从 UI 下拉框中隐藏
- 需要：模型格式转换（safetensors → ONNX）或新增 Transformers 引擎

---

## 五、关键文件地图

### 前端核心
| 文件 | 职责 |
|------|------|
| `src/App.vue` | 主布局（topbar / left-rail / workbench / right-review / bottombar） |
| `src/main.js` | Vue 入口、全局错误拦截、Pinia |
| `src/stores/taskStore.js` | 任务状态中心（single source of truth） |
| `src/stores/configStore.js` | 配置持久化 |
| `src/components/UploadZone.vue` | 上传 + 队列 + 批量处理 |
| `src/components/ResultPanel.vue` | 结果展示（raw/polished/diff） |
| `src/components/ConfigDrawer.vue` | 配置抽屉 |
| `src/components/AIProviderCenter.vue` | AI 方案管理 |
| `src/components/ToastStack.vue` | Toast 容器 |
| `src/components/DialogSystem.vue` | 模态弹窗 |
| `src/composables/useAIStream.js` | AI 流式处理 |
| `src/composables/useToast.js` | Toast API |
| `src/composables/useDialog.js` | Dialog API |
| `src/composables/useNotify.js` | Windows 通知 |
| `src/api/tauri_ipc.js` | Tauri IPC + HTTP 桥接 |

### 后端核心
| 文件 | 职责 |
|------|------|
| `backend/main.py` | FastAPI 入口、生命周期、队列启动 |
| `backend/api/routes.py` | 所有 HTTP 路由 + WebSocket |
| `backend/ai_refiner/refiner.py` | AIRefiner 类（prompt、API 调用、failover） |
| `backend/ai_refiner/__init__.py` | 导出 |
| `backend/config/settings.py` | UserConfig / AIScheme / ConfigManager |
| `backend/core/ocr_engine.py` | OCREngineManager |
| `backend/task_queue/local_queue.py` | 批量队列（Semaphore 控制并发） |
| `backend/scene/classifier.py` | 场景分类器 |
| `backend/preprocess/pipeline.py` | 预处理流水线 |

### Rust 核心
| 文件 | 职责 |
|------|------|
| `src-tauri/src/main.rs` | Tauri 入口、IPC 命令、Python Sidecar、Tray |
| `src-tauri/Cargo.toml` | 依赖（tauri v2 + notification/shell/opener） |
| `src-tauri/capabilities/default.json` | 权限配置 |

---

## 六、开发环境注意事项

### 启动命令（不要用 `cargo tauri dev`！）
```powershell
# Terminal 1: Vite
node node_modules/vite/bin/vite.js

# Terminal 2: Tauri
cd src-tauri; cargo run
```

### 常见坑
1. **PowerShell 执行策略**：若 npm 脚本被阻，用 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
2. **Vite HMR 缓存异常**：`rm -rf node_modules/.vite` 后重启
3. **端口占用**：见上文 workaround
4. **Rust 编译缓存**：修改 `main.rs` 后 `cargo run` 会自动增量编译

---

## 七、当前环境状态

| 组件 | 状态 | 备注 |
|------|------|------|
| Vite | ✅ 运行中 | port 1420 |
| Tauri Rust | ❌ 已 kill | 需重启 `cargo run` |
| Python Sidecar | ❌ 已 kill | 随 Tauri 重启 |
| Git | 19 files changed, +2177/-709 | 未 commit |

---

## 八、下一步建议（按优先级）

1. **重启 Tauri**，验证 AI Refiner JSON 修复是否生效
2. **如果仍报错**，检查后端日志 `logs/backend.log` 中的 `_call_scheme` 输出
3. **确认用户配置**：`config.json` 中 `ai.enabled=true` 且 API Key 有效
4. **如果 LLM 仍不返回严格 JSON**：
   - 方案 A：去掉 `response_format`，改用文本提取 JSON
   - 方案 B：增加 `max_tokens` + 更严格的 prompt
5. **修复批量任务的 AI Refiner**（`main.py` `recognize_sync_wrapper`）
