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
    return invoke('get_python_port')
  }
  return 8000
}

// OCR 单图识别
export async function ocrRecognize(imageBase64, options = {}) {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('ocr_recognize', {
      imageBase64,
      options: JSON.stringify(options),
    })
  }
  const res = await fetch('http://localhost:8000/v1/ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64, options }),
  })
  return res.json()
}

// 批量 OCR 提交
export async function ocrBatch(images, options = {}) {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('ocr_batch', {
      images,
      options: JSON.stringify(options),
    })
  }
  const res = await fetch('http://localhost:8000/v1/ocr/batch/json', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ images, options }),
  })
  return res.json()
}

// 获取批量任务状态
export async function getBatchStatus(taskId) {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('get_batch_status', { taskId })
  }
  const res = await fetch(`http://localhost:8000/v1/ocr/batch/${taskId}`)
  return res.json()
}

// 取消批量任务
export async function cancelBatch(taskId) {
  const port = await getPythonPort()
  const res = await fetch(`http://127.0.0.1:${port}/v1/ocr/batch/${taskId}/cancel`, {
    method: 'POST',
  })
  return res.json()
}

// 创建 WebSocket 连接监听批量任务进度
export async function createBatchWebSocket(taskId, onMessage) {
  const port = await getPythonPort()
  const wsUrl = `ws://127.0.0.1:${port}/ws/batch/${taskId}`
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected:', taskId)
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
    console.log('WebSocket closed:', taskId)
  }

  return ws
}

// 获取可用模型列表
export async function getAvailableModels() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('get_available_models')
  }
  const res = await fetch('http://localhost:8000/v1/models')
  return res.json()
}

// 拉取模型
export async function pullModel(modelId) {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('pull_model', { modelId })
  }
  const res = await fetch(`http://localhost:8000/v1/models/${modelId}/pull`, {
    method: 'POST',
  })
  return res.json()
}

// 获取配置
export async function getConfig() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('get_config')
  }
  const res = await fetch('http://localhost:8000/v1/config')
  return res.json()
}

// 保存配置
export async function saveConfig(config) {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('save_config', { config: JSON.stringify(config) })
  }
  const res = await fetch('http://localhost:8000/v1/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return res.json()
}

// 打开模型目录
export async function openModelDir() {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke('open_model_dir')
  }
  console.warn('openModelDir: 仅在 Tauri 桌面环境中可用')
}
