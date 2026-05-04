# VonishOCR 已知 Bug 全清单

> 更新日期：2026-05-02
> 基于 commit `da4da18` + 后续所有修复

---

## 一、已修复（代码已改，需验证生效）

### Bug 1：ConfigDrawer.vue `ref is not defined`
- **现象**：打开设置抽屉时 Console 报错 `Uncaught ReferenceError: ref is not defined`
- **根因**：`<script setup>` 中使用了 `ref()` 但 import 只写了 `import { reactive, watch } from 'vue'`，漏了 `ref`
- **修复**：第 94 行改为 `import { ref, reactive, watch } from 'vue'`
- **验证**：打开设置抽屉，Console 无报错
- **状态**：✅ 代码已修复

### Bug 2：托盘图标 `.unwrap()` panic
- **现象**：Tauri 启动时 panic，窗口无法弹出
- **根因**：`main.rs` 第 306 行 `app.default_window_icon().cloned()` 在开发模式下返回 `None`，后续 `.unwrap()` panic
- **修复**：改为 `if let Some(icon) = icon { tray_builder = tray_builder.icon(icon); }`
- **验证**：Tauri 正常启动，托盘出现
- **状态**：✅ 代码已修复

### Bug 3：Python sidecar `logging.handlers` 未导入
- **现象**：Python 启动即崩溃，Tauri 窗口卡在 splash
- **根因**：`main.py` 第 250 行使用 `logging.handlers.RotatingFileHandler` 但只 `import logging`，未 `import logging.handlers`
- **修复**：第 7 行添加 `import logging.handlers`
- **验证**：Tauri 启动后 Python sidecar 正常输出 ready 信号
- **状态**：✅ 代码已修复

### Bug 4：tauri_ipc.js IPC 调用返回 JSON 字符串而非对象
- **现象**：单图识别后 ResultPanel 空白；批量识别后 `task_id` 为 undefined
- **根因**：Rust IPC `ocr_recognize` / `ocr_batch` 等返回 `Result<String, String>`，Tauri `invoke` 传给前端的是 JSON 字符串。非 Tauri 模式（浏览器开发）用 `res.json()` 正确，Tauri 模式直接返回字符串
- **修复**：`tauri_ipc.js` 添加 `_parseJson(text)` 函数，所有 IPC 调用在 Tauri 模式下先 `JSON.parse()`
- **验证**：Console 打印 `ocrRecognize` 返回值，确认是对象而非字符串
- **状态**：✅ 代码已修复

### Bug 5：批量路径结果未写入 Pinia Store
- **现象**：上传多图批量识别后，ResultPanel 空白
- **根因**：`UploadZone.vue` WebSocket 回调只更新进度条和文件状态（`selected[i].status = 'done'`），**没有把 OCR 结果写入 `taskStore.results`**。后端 `LocalQueue` 存储了结果，但 routes.py **没有暴露获取批量结果的 HTTP 接口**
- **修复**：
  1. `routes.py` 新增 `GET /v1/ocr/batch/{task_id}/results`
  2. `main.rs` 新增 `get_batch_results` IPC 命令
  3. `tauri_ipc.js` 新增 `getBatchResults()`
  4. `UploadZone.vue` 批量完成后调用 `getBatchResults()` 并按顺序写入 store
- **验证**：批量 3 张图，完成后点击每张图，ResultPanel 显示识别文本
- **状态**：🔧 代码已修复，**效果待用户验证**

### Bug 6：批量 9 张图卡死 + 显存暴涨到 15GB
- **现象**：拖 9 张图后 Python 进程内存极大，任务管理器显示 GPU 内存 15GB，进度条不动
- **根因**：
  1. `LocalQueue` concurrency = 8，8 个线程同时通过 `asyncio.to_thread` 做 DirectML 推理
  2. DirectML + ONNX Runtime 为每个并发线程分配独立 GPU 工作缓冲区
  3. `recognize_sync_wrapper` 处理完后不调用 `gc.collect()`，临时 numpy 数组堆积
  4. `OCREngineManager.recognize_sync` 在线程中无运行事件循环，反复 `asyncio.run(coro)` 创建/销毁事件循环
- **修复**：
  1. `local_queue.py` concurrency 8 → 3
  2. `process_one` finally 块中添加 `gc.collect()`
  3. `main.py` `recognize_sync_wrapper` 末尾添加 `del` + `gc.collect()`
  4. `ocr_engine.py` `recognize_sync` 改为 `coro.send(None)` 避免 `asyncio.run()`
- **验证**：拖 9 张图，任务管理器 GPU 内存峰值 < 6GB，进度正常推进
- **状态**：🔧 代码已修复，**效果待用户验证**

### Bug 7：单图误走批量路径（已完成的旧文件干扰）
- **现象**：只上传 1 张图，却走了批量路径（有进度条）
- **根因**：`UploadZone.vue` 的 `files` 数组不清除已完成的文件。之前上传的文件仍 `selected: true`，导致 `selectedFiles.length > 1`
- **修复**：`startOCR()` 开头遍历 files，把 `status === 'done' || 'failed'` 的文件的 `selected` 设为 `false`
- **验证**：先上传 1 张图识别完成，再上传 1 张新图，确认走单图路径（无批量进度条）
- **状态**：🔧 代码已修复，**效果待用户验证**

---

## 二、未修复（代码中仍然存在）

### Bug 8：两套 id 系统并存（根本架构问题）
- **现象**：`taskStore.currentTask.id` 和 `taskStore.setResult()` 的 key **可能不一致**，导致 ResultPanel 读取不到结果
- **根因**：
  - `UploadZone.vue` 中 `file.id = ++idCounter`（自增数字，从 1 开始）
  - `taskStore.addFiles()` 中 `task.id = crypto.randomUUID()`（字符串 UUID）
  - `UploadZone.vue` 和 `taskStore.tasks` 维护**两个独立的数组**
  - `selectFile(file)` 把 `taskStore.currentTask` 设为 UploadZone 的 `file` 对象（数字 id）
  - `taskStore.setResult(file.id, result)` 使用数字 id 存储
  - `ResultPanel` 通过 `taskStore.getResult(current.id)` 读取，current 是 UploadZone 的 file（数字 id）
  - **理论上匹配**，但如果用户从其他组件（如 taskStore.tasks 列表）点击任务，currentTask 会变成 UUID id 的对象，和 setResult 的 key 不匹配
- **影响**：单图路径下如果 id 不匹配，ResultPanel 空白；批量路径下如果顺序错乱，结果和文件对应错误
- **修复建议**：
  - 方案 A：UploadZone 直接使用 `taskStore.tasks` 作为文件列表，不维护独立的 `files` 数组
  - 方案 B：UploadZone 的 `file.id` 也用 `crypto.randomUUID()`，与 taskStore 一致
- **状态**：❌ 未修复，**可能是 ResultPanel 空白的隐藏根因**

### Bug 9：ResultPanel fallback 提示文字被误读为"空白"
- **现象**：用户报告"没有任何文字展示，一片空白"
- **根因**：`displayResult` computed 在 `rawResult.value === null` 时返回 fallback：
  ```
  '请上传图片并运行识别...\n(选择左侧文件后点击"开始识别")'
  ```
  这段文字是灰色的、在浅灰色背景（`#f9f9fb`）上，视觉上可能不够明显。加上 `tab-pane { height: 100% }` 可能导致 flex 布局异常，文字被推到不可见区域。
- **影响**：用户以为"空白"，实际上有提示文字
- **修复建议**：
  1. 把 fallback 文字颜色加深（`#666` → `#333`）
  2. 把 `tab-pane { height: 100% }` 去掉或改为 `min-height: 200px`
  3. 在 `content` div 为空时显示一个显眼的空状态插画/图标
- **状态**：❌ 未修复

### Bug 10：AI Refiner 的 `scene_type` 参数硬编码
- **现象**：AI Refiner 的 prompt 中场景标签永远是 `"print"`
- **根因**：`routes.py` 第 140 行 `scene_type = options.get("scene", "print")`，但 `options` 字典中从未传递 `scene` 字段。场景分类器已经识别出了正确场景（如 `"screenshot"`、`"handwritten_note"`），但没有传给 AI Refiner
- **影响**：AI 修复的场景感知能力打折扣，prompt 中的场景指导不准确
- **修复建议**：把 `ocr_single` 中 `scene_type` 变量的值（已正确识别）传给 `refiner.refine(scene_type=scene_type)`
- **状态**：❌ 未修复（轻微，不影响核心功能）

### Bug 11：模型下载（pull_model）是 stub
- **现象**：点击"拉取模型"按钮，提示 `"Phase 0 stub - download not implemented"`
- **根因**：`routes.py` 第 242 行 `pull_model` 直接返回 stub 消息，`model_puller.py` 未实现下载逻辑
- **影响**：用户无法通过 UI 下载新模型，只能手动放到 `models/` 目录
- **修复建议**：实现 `model_puller.py` 的下载逻辑（HTTP 下载 + SHA256 校验 + 解压）
- **状态**：❌ 未实现

### Bug 12：WebSocket 进度推送不包含识别结果
- **现象**：批量任务完成后，前端需要额外发送一次 HTTP GET 请求获取结果
- **根因**：`_ws_progress_callback` 只推送 `{type: "progress", completed, total}`，没有推送 `result`。导致前端必须轮询或等完成后再 GET `/results`
- **影响**：增加了不必要的 HTTP 请求，延迟了结果显示
- **修复建议**：在 `_ws_progress_callback` 中把 `results[idx]` 一起推送：`{type: "progress", completed, total, result: {...}}`。前端收到后实时写入 store
- **状态**：❌ 未修复（设计选择，但可优化）

### Bug 13：识别结果不持久化
- **现象**：刷新页面或重启应用后，之前的识别结果全部丢失
- **根因**：`taskStore.results` 是内存中的 `ref({})`，没有持久化到磁盘
- **影响**：用户无法回顾历史识别结果
- **修复建议**：
  - 方案 A：使用 Tauri 的 fs API 把结果保存到 `results/` 目录（每张图一个 JSON）
  - 方案 B：使用 IndexedDB（浏览器 API，Tauri 也支持）
- **状态**：❌ 未实现

### Bug 14：`recognize_sync` 的协程执行方式仍有隐患
- **现象**：`OCREngineManager.recognize_sync` 中 `coro.send(None)` 可能不适用于所有引擎实现
- **根因**：当前修复把 `asyncio.run(coro)` 改为 `coro.send(None)`，假设"引擎内部无 await，一次 send 即可跑完"。但如果未来换了引擎（如 PaddleOCR），其 `recognize` 方法内部可能有真正的 await 点，此时 `send(None)` 会返回一个待执行的协程对象，不会真正完成识别
- **影响**：未来扩展引擎时可能踩坑
- **修复建议**：为每个引擎提供真正的同步方法 `recognize_sync()`，而不是把 async 方法当 sync 调用
- **状态**：❌ 未修复（当前可用，但架构脆弱）

### Bug 15：前端错误处理代码重复
- **现象**：`UploadZone.vue` 中单图错误处理和批量错误处理各写了一遍几乎相同的解析逻辑
- **根因**：代码复制粘贴，没有抽象统一的错误解析函数
- **影响**：维护困难，改一处容易漏另一处
- **修复建议**：在 `tauri_ipc.js` 或 `taskStore.js` 中封装 `parseApiError(e)` 函数
- **状态**：❌ 未修复

### Bug 16：Vite 开发服务器缓存问题
- **现象**：修改代码后前端没有热重载，或浏览器缓存了旧文件
- **根因**：`node node_modules/vite/bin/vite.js` 直接启动时，Vite 的模块缓存和浏览器缓存可能导致旧代码残留
- **影响**：开发者以为修复无效，实际上是缓存未刷新
- **修复建议**：
  - 开发时在 `vite.config.js` 中配置 `server: { hmr: { overlay: false } }`
  - 在 `index.html` 中添加 `<meta http-equiv="Cache-Control" content="no-cache">`
- **状态**：❌ 未根治（当前靠手动 `Ctrl+F5` + 清除 `node_modules/.vite`）

### Bug 17：PowerShell 执行策略阻止 npm 脚本
- **现象**：`npm run dev` 报错 `"无法加载 npm.ps1，因为在此系统上禁止运行脚本"`
- **根因**：Windows 默认 `Restricted` 执行策略
- **影响**：无法直接用 `npm run dev` 启动 Vite
- **workaround**：改用 `node node_modules/vite/bin/vite.js` 直接启动
- **修复建议**：在 README 中注明需要 `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
- **状态**：❌ 未根治（有 workaround）

---

## 三、潜在风险（代码审查发现）

### Risk 1：`file.status = 'done'` 可能不触发 ResultPanel 重新渲染
- **分析**：`file` 是 `files.value` 数组中的响应式对象。`taskStore.currentTask = file` 后，`currentTask` 引用同一个对象。`file.status = 'done'` 修改了该对象，`isLoading` computed（依赖 `current.status`）应该重新计算。**但如果 Vue 的响应性追踪失效（比如对象被冻结或替换），`isLoading` 可能仍为 true**
- **验证方法**：在 `isLoading` computed 中加 `console.log('isLoading:', current?.status, !!rawResult.value)`

### Risk 2：`taskStore.currentTask` 可能在不同组件间被覆盖
- **分析**：`currentTask` 是一个全局 ref，任何组件都可以修改。如果 ConfigDrawer 或其他未来组件也修改了 `currentTask`，ResultPanel 可能显示错误任务的结果
- **建议**：把 `currentTask` 改为只读 getter，通过 `setCurrentTask(id)` action 来修改

### Risk 3：DirectML 的显存释放不可控
- **分析**：DirectML 使用 WDDM 驱动，显存分配由操作系统管理。`gc.collect()` 只释放 Python 对象，不保证 GPU 内存立即回收。ONNX Runtime 的 arena 分配器会保留已分配的 GPU 内存供下次复用
- **建议**：任务完成后添加 `onnxruntime.InferenceSession` 级别的内存清理（如果有 API），或监控 `nvidia-smi` 确认实际占用

### Risk 4：`models/` 目录扫描失败时崩溃
- **分析**：`ONNXOCREngine._scan_models()` 在模型文件缺失时抛出 `FileNotFoundError`。如果用户手动删除了模型文件，应用启动时预加载会失败，但 lifespan 中 try-except 捕获了异常，不会导致整个后端崩溃
- **状态**：已有保护，但用户体验差（模型消失无提示）

### Risk 5：批量任务的取消可能不彻底
- **分析**：`LocalQueue.cancel()` 会设置 cancel_event 并清空队列，但正在 `asyncio.to_thread` 中执行的线程**无法被强制中断**。取消只影响还未开始的图片，已在处理的图片会继续跑完
- **建议**：添加线程级别的中断机制（如全局标志位），或接受"取消 = 停止接收新任务，已开始的任务跑完"的行为

---

## 四、Bug 影响矩阵

| Bug | 影响范围 | 严重程度 | 修复难度 | 优先级 |
|-----|---------|---------|---------|--------|
| 8 两套 id 系统 | 单图+批量结果展示 | 🔴 高 | 🟡 中（需重构）| P0 |
| 9 fallback 被误读 | 用户体验 | 🟡 中 | 🟢 低 | P1 |
| 10 AI scene 硬编码 | AI 修复质量 | 🟢 低 | 🟢 低 | P2 |
| 11 模型下载 stub | 功能缺失 | 🟡 中 | 🟡 中 | P1 |
| 12 WebSocket 不含结果 | 批量延迟 | 🟡 中 | 🟢 低 | P2 |
| 13 结果不持久化 | 数据丢失 | 🟡 中 | 🟡 中 | P2 |
| 14 recognize_sync 隐患 | 未来扩展 | 🟢 低 | 🟡 中 | P3 |
| 15 错误处理重复 | 维护性 | 🟢 低 | 🟢 低 | P3 |
| 16 Vite 缓存 | 开发体验 | 🟡 中 | 🟢 低 | P2 |
| 17 PowerShell 策略 | 开发体验 | 🟡 中 | 🟢 低 | P2 |

---

## 五、诊断建议（给接手开发者）

如果你要 Debug ResultPanel 空白，按这个顺序排查：

### Step 1：确认数据是否到达前端
在 DevTools Console 执行：
```javascript
// 1. 确认 currentTask 是什么
console.log('currentTask:', JSON.parse(JSON.stringify(taskStore.currentTask)))

// 2. 确认 results 的 key
console.log('results keys:', Object.keys(taskStore.results))

// 3. 确认 currentTask.id 是否在 results 中
const id = taskStore.currentTask?.id
console.log('has result?', id !== undefined && taskStore.results[id] !== undefined)

// 4. 如果有结果，打印结果结构
if (id !== undefined) {
  console.log('result:', JSON.parse(JSON.stringify(taskStore.results[id])))
}
```

**如果 `has result?` 为 false** → Bug 8（id 不匹配）或 Bug 5（批量结果未写入）
**如果 `has result?` 为 true 但 `text` 为空** → 后端返回的 JSON 中 `text` 字段为空

### Step 2：确认单图路径还是批量路径
```javascript
// 在上传文件后、点击识别前执行
console.log('selected files count:', 
  taskStore.tasks.filter(t => t.selected).length
)
```
如果 > 1，走的是批量路径。

### Step 3：确认 IPC 返回格式
在 `tauri_ipc.js` 的 `ocrRecognize` 函数中加 log：
```javascript
export async function ocrRecognize(imageBase64, options = {}) {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    const text = await invoke('ocr_recognize', { ... })
    console.log('IPC raw:', typeof text, text.slice(0, 100))  // ← 加这行
    return _parseJson(text)
  }
  // ...
}
```
如果 `typeof text === 'object'`，说明 Tauri 已经在内部 parse 了，`_parseJson` 会原样返回，这是正常的。
如果 `typeof text === 'string'`，说明 `_parseJson` 正在工作。

### Step 4：确认后端返回的 JSON
```powershell
curl -X POST http://127.0.0.1:{port}/v1/ocr `
  -H "Content-Type: application/json" `
  -d '{"image": "data:image/png;base64,iVBORw0KGgo..."}'
```
确认返回的 JSON 中有 `"text"` 字段且非空。
