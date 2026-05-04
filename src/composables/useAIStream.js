import { ref } from 'vue'
import { streamAIRefine, parseApiError } from '../api/tauri_ipc'

export function useAIStream() {
  const status = ref('idle')
  const text = ref('')
  const diff = ref([])
  const error = ref(null)
  const providerResult = ref(null)
  let controller = null

  async function start(payload) {
    stop(true)
    controller = new AbortController()
    status.value = 'streaming'
    text.value = ''
    diff.value = []
    error.value = null
    providerResult.value = null

    try {
      await streamAIRefine(payload, {
        signal: controller.signal,
        onEvent(event) {
          if (event.type === 'start') {
            // start 事件已由后端发送，status 已经是 streaming
          } else if (event.type === 'token') {
            text.value += event.token || ''
          } else if (event.type === 'diff') {
            diff.value = event.diff || []
          } else if (event.type === 'error') {
            error.value = new Error(event.message || 'AI 修复失败')
            status.value = 'error'
          } else if (event.type === 'done') {
            providerResult.value = event.result || null
            if (event.result?.polished) text.value = event.result.polished
            diff.value = event.result?.diff || diff.value
            if (event.result?.error) {
              error.value = new Error(event.result.error.message || 'AI 修复失败')
              status.value = 'error'
            } else {
              status.value = 'done'
            }
          }
        },
      })
      if (status.value === 'streaming') status.value = 'done'
    } catch (e) {
      if (e?.name === 'AbortError') {
        status.value = 'interrupted'
        return
      }
      const parsed = parseApiError(e, 'AI 修复请求失败')
      error.value = new Error(parsed.message)
      status.value = 'error'
    } finally {
      controller = null
    }
  }

  function stop(silent = false) {
    if (controller) {
      controller.abort()
      controller = null
      if (!silent) status.value = 'interrupted'
    }
  }

  return {
    status,
    text,
    diff,
    error,
    providerResult,
    start,
    stop,
  }
}
