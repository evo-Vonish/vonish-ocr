import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ocrRecognize, ocrBatch, getBatchStatus } from '../api/tauri_ipc'

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const isProcessing = ref(false)
  const results = ref({})

  // Getters
  const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)
  const processingCount = computed(() => tasks.value.filter(t => t.status === 'processing').length)
  const doneCount = computed(() => tasks.value.filter(t => t.status === 'done').length)
  const failedCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)

  // Actions
  function addFiles(fileList) {
    for (const file of fileList) {
      tasks.value.push({
        id: crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random(),
        name: file.name,
        size: file.size,
        status: 'pending',
        selected: true,
        thumb: file.thumb || null,
        base64: file.base64 || null,
      })
    }
  }

  function removeTask(taskId) {
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx !== -1) tasks.value.splice(idx, 1)
  }

  function clearCompleted() {
    tasks.value = tasks.value.filter(t => t.status !== 'done')
  }

  function setTaskStatus(taskId, status) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) task.status = status
  }

  async function recognizeSingle(imageBase64, options = {}) {
    isProcessing.value = true
    try {
      const result = await ocrRecognize(imageBase64, options)
      return result
    } catch (e) {
      console.error('OCR 识别失败:', e)
      throw e
    } finally {
      isProcessing.value = false
    }
  }

  async function submitBatch(imageList, options = {}) {
    isProcessing.value = true
    try {
      const result = await ocrBatch(imageList, options)
      return result
    } catch (e) {
      console.error('批量提交失败:', e)
      throw e
    } finally {
      isProcessing.value = false
    }
  }

  async function pollBatchStatus(taskId, interval = 1000) {
    const poll = async () => {
      try {
        const status = await getBatchStatus(taskId)
        return status
      } catch (e) {
        console.error('轮询状态失败:', e)
        return null
      }
    }
    return poll()
  }

  function setResult(taskId, result) {
    results.value[taskId] = result
  }

  function getResult(taskId) {
    return results.value[taskId] || null
  }

  return {
    tasks,
    currentTask,
    isProcessing,
    results,
    pendingCount,
    processingCount,
    doneCount,
    failedCount,
    addFiles,
    removeTask,
    clearCompleted,
    setTaskStatus,
    recognizeSingle,
    submitBatch,
    pollBatchStatus,
    setResult,
    getResult,
  }
})
