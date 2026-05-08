/**
 * 解析 Rust IPC 返回的 JSON 字符串（Tauri invoke 返回 String 而非 Object）
 */
import { showToast } from '../composables/useToast'

function _parseJson(text) {
  if (typeof text === 'string') {
    const trimmed = text.trim()
    if (!trimmed) {
      console.error('[_parseJson] 后端返回空响应')
      showToast({ type: 'error', message: '后端无响应，Python sidecar 可能已崩溃', duration: 5000 })
      throw new Error('后端无响应，请重启应用')
    }
    try {
      const data = JSON.parse(trimmed)
      if (data?.detail?.code) {
        throw data
      }
      return data
    } catch (e) {
      if (e?.detail?.code) throw e
      console.error('[_parseJson] 后端返回非JSON:', trimmed.slice(0, 500))
      showToast({ type: 'error', message: '后端响应格式错误，请重启应用后重试', duration: 5000 })
      throw new Error('后端响应格式错误: ' + trimmed.slice(0, 200))
    }
  }
  if (text?.detail?.code) throw text
  return text
}

export function parseApiError(error, fallbackMessage = '请求失败，请重试') {
  let parsed = error
  if (typeof error === 'string') {
    try {
      parsed = JSON.parse(error)
    } catch (_) {
      return { code: 'UNKNOWN', message: error || fallbackMessage }
    }
  }

  if (parsed?.detail?.code) {
    return {
      code: parsed.detail.code,
      message: parsed.detail.message || fallbackMessage,
    }
  }
  if (parsed?.code) {
    return {
      code: parsed.code,
      message: parsed.message || fallbackMessage,
    }
  }
  if (parsed?.message) {
    return { code: 'UNKNOWN', message: parsed.message }
  }
  return { code: 'UNKNOWN', message: fallbackMessage }
}

async function _jsonOrThrow(res) {
  const text = await res.text()
  const data = text ? _parseJson(text) : {}
  if (!res.ok) {
    throw data
  }
  return data
}

async function _backendUrl(path) {
  const port = await getPythonPort()
  return `http://127.0.0.1:${port}${path}`
}

async function _backendJson(path, options = {}) {
  const res = await fetch(await _backendUrl(path), options)
  return _jsonOrThrow(res)
}

/**
 * Tauri IPC 封装层
 * 统一封装所有后端调用，在 Tauri 环境下走 invoke，浏览器开发模式 fallback 到 HTTP
 */

const isTauri = () => {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined
}

// 获取 Python sidecar 端口（Tauri 模式下需要）
export async function getPythonPort() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    for (let i = 0; i < 30; i++) {
      const port = Number(await invoke('get_python_port').catch(() => 0))
      if (port > 0) return port
      await new Promise(resolve => setTimeout(resolve, 150))
    }
    throw new Error('Python sidecar 尚未就绪，请稍后重试')
  }
  return 8000
}

// OCR 单图识别
export async function ocrRecognize(imageBase64, options = {}) {
  const { preprocess_job_id, skip_preprocess, preprocess_strategy, scene_override, config_override, ...ocrOptions } = options || {}
  return _backendJson('/v1/ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64, options: ocrOptions, preprocess_job_id, skip_preprocess, preprocess_strategy, scene_override, config_override }),
  })
}

// 批量 OCR 提交
export async function preprocessImage(payload) {
  return _backendJson('/v1/preprocess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getPreprocessImageUrl(jobId, kind = 'processed') {
  return _backendUrl(`/v1/preprocess/${jobId}/${kind}`)
}

export async function ocrBatch(images, options = {}) {
  return _backendJson('/v1/ocr/batch/json', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ images, options }),
  })
}

// 获取批量任务结果
export async function getBatchResults(taskId) {
  return _backendJson(`/v1/ocr/batch/${taskId}/results`)
}

// 获取批量任务状态
export async function getBatchStatus(taskId) {
  return _backendJson(`/v1/ocr/batch/${taskId}`)
}

// 取消批量任务
export async function cancelBatch(taskId) {
  return _backendJson(`/v1/ocr/batch/${taskId}/cancel`, {
    method: 'POST',
  })
}

// 创建 WebSocket 连接监听批量任务进度（带断线重连）
export async function createBatchWebSocket(taskId, onMessage) {
  const port = await getPythonPort()
  const wsUrl = `ws://127.0.0.1:${port}/ws/batch/${taskId}`
  const RECONNECT_INTERVAL = 3000 // 3秒
  const MAX_RECONNECT = 5
  let reconnectCount = 0
  let ws = null
  let closed = false

  function connect() {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      reconnectCount = 0
    }
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        onMessage(msg)
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }
    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
    }
    ws.onclose = () => {
      if (!closed && reconnectCount < MAX_RECONNECT) {
        reconnectCount++
        setTimeout(connect, RECONNECT_INTERVAL)
      }
    }
  }

  connect()

  return {
    close: () => {
      closed = true
      if (ws) ws.close()
    },
    send: (data) => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(data)
    },
  }
}

// 获取可用模型列表
export async function getAvailableModels() {
  return _backendJson('/v1/models')
}

// 拉取模型
export async function pullModel(modelId) {
  return _backendJson(`/v1/models/${modelId}/pull`, {
    method: 'POST',
  })
}

// 获取配置
export async function getConfig() {
  return _backendJson('/v1/config')
}

// 保存配置
export async function saveConfig(config) {
  return _backendJson('/v1/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
}

// AI 方案列表。Key 由后端加密存储，这里只拿 key_saved 状态。
export async function getAISchemes() {
  return _backendJson('/v1/ai/schemes')
}

// 新增或更新 AI 方案；api_key 只在本次请求内传输，不写入 localStorage。
export async function saveAIScheme(scheme) {
  return _backendJson('/v1/ai/schemes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scheme),
  })
}

export async function setActiveAIScheme(schemeId) {
  return _backendJson('/v1/ai/schemes/active', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheme_id: schemeId }),
  })
}

export async function streamAIRefine(payload, { signal, onEvent } = {}) {
  const port = await getPythonPort()
  const url = `http://127.0.0.1:${port}/v1/ai/refine/stream`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) {
    const err = await _jsonOrThrow(res)
    throw err
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      const line = chunk.split('\n').find(part => part.startsWith('data: '))
      if (!line) continue
      const event = JSON.parse(line.slice(6))
      onEvent?.(event)
    }
  }
}

export async function getBackendConsoleStatus() {
  return _backendJson('/v1/console/status')
}

export async function testBackendRequest() {
  return _backendJson('/health')
}

// 控制台模型切换：走后端真实卸载 / 加载接口，并返回步骤结果。
export async function switchConsoleModel(modelId) {
  return _backendJson('/v1/console/model/switch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  })
}

// 控制台缓存清理：只释放模型驻留，不删除本地模型文件。
export async function clearConsoleCache() {
  return _backendJson('/v1/console/cache/clear', {
    method: 'POST',
  })
}

// 控制台性能模式：由后端按真实硬件重新计算安全并发，并同步到 LocalQueue。
export async function applyConsolePerformance(mode, overrides = {}) {
  return _backendJson('/v1/console/performance/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, overrides }),
  })
}

// 服务化队列 API：供后端控制台实时任务面板接入。
export async function getServiceQueueTasks(limit = 100) {
  return _backendJson(`/v1/queue/tasks?limit=${encodeURIComponent(limit)}`)
}

export async function getServiceQueueTask(taskId) {
  return _backendJson(`/v1/queue/status/${encodeURIComponent(taskId)}`)
}

export async function cancelServiceQueueTask(taskId) {
  return _backendJson(`/v1/queue/cancel/${encodeURIComponent(taskId)}`, { method: 'POST' })
}

export async function retryServiceQueueTask(taskId) {
  return _backendJson(`/v1/queue/retry/${encodeURIComponent(taskId)}`, { method: 'POST' })
}

export async function getApiKeys() {
  return _backendJson('/v1/admin/keys')
}

export async function createApiKey(payload) {
  return _backendJson('/v1/admin/keys', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function revokeApiKey(keyOrPrefix) {
  return _backendJson(`/v1/admin/keys/${encodeURIComponent(keyOrPrefix)}`, { method: 'DELETE' })
}

// 查询 Tauri 管理的 sidecar 状态。停止服务后 HTTP 不可用，所以必须走原生命令。
export async function getBackendServiceState() {
  if (!isTauri()) {
    return { status: 'running', port: 8000, pid: null }
  }
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke('backend_service_status')
}

// 控制 Python sidecar 启停 / 重启。这里不能走 HTTP，否则停止后就无法再启动。
export async function controlBackendService(action) {
  if (!isTauri()) {
    return { status: action === 'stop' ? 'stopped' : 'running', port: 8000, pid: null }
  }
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke('control_backend_service', { action })
}

// 打开模型目录
export async function openModelDir() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('open_model_dir')
  }
  console.warn('openModelDir: 仅在 Tauri 桌面环境中可用')
}

// 打开后端日志目录
export async function openBackendConsole() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('open_backend_console')
  }
  window.open('/logs/', '_blank')
}

// 打开项目文档
export async function openDocs() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('open_docs')
  }
  window.open('/README.md', '_blank')
}
