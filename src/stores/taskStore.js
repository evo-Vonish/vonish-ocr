import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ocrRecognize, ocrBatch, getBatchStatus } from '../api/tauri_ipc'

const STORAGE_KEY = 'vonish-ocr:task-state:v1'

function createId() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
}

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref([])
  const currentTaskId = ref(null)
  const isProcessing = ref(false)
  const results = ref({})
  const errors = ref({})

  // Getters
  const currentTask = computed(() => {
    if (!currentTaskId.value) return null
    return tasks.value.find(t => t.id === currentTaskId.value) || null
  })
  const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)
  const processingCount = computed(() => tasks.value.filter(t => t.status === 'processing').length)
  const doneCount = computed(() => tasks.value.filter(t => t.status === 'done').length)
  const failedCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)
  const selectedTasks = computed(() => tasks.value.filter(t => t.selected))

  function persist() {
    if (!canUseStorage()) return
    try {
      const lightweightTasks = tasks.value.map(({ base64, thumb, ...task }) => ({
        ...task,
        selected: false,
        restored: !base64,
      }))
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
        tasks: lightweightTasks,
        currentTaskId: currentTaskId.value,
        results: results.value,
        errors: errors.value,
      }))
    } catch (e) {
      console.warn('持久化 OCR 结果失败:', e)
    }
  }

  function restorePersisted() {
    if (!canUseStorage()) return
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const data = JSON.parse(raw)
      tasks.value = Array.isArray(data.tasks)
        ? data.tasks.map(t => ({
            ...t,
            status: t.status === 'processing' || t.status === 'queued' ? 'pending' : t.status,
            selected: false,
            thumb: null,
            base64: null,
            restored: true,
          }))
        : []
      results.value = data.results || {}
      errors.value = data.errors || {}
      currentTaskId.value = tasks.value.some(t => t.id === data.currentTaskId)
        ? data.currentTaskId
        : (tasks.value[0]?.id || null)
    } catch (e) {
      console.warn('恢复 OCR 结果失败:', e)
    }
  }

  // Actions
  function addFiles(fileList) {
    const added = []
    for (const file of fileList) {
      const task = {
        id: file.id || createId(),
        name: file.name,
        size: file.size,
        status: 'pending',
        selected: true,
        thumb: file.thumb || null,
        base64: file.base64 || null,
        restored: false,
      }
      tasks.value.push(task)
      added.push(task)
    }
    if (!currentTaskId.value && added.length) currentTaskId.value = added[0].id
    persist()
    return added
  }

  function removeTask(taskId) {
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx !== -1) tasks.value.splice(idx, 1)
    delete results.value[taskId]
    delete errors.value[taskId]
    if (currentTaskId.value === taskId) currentTaskId.value = tasks.value[0]?.id || null
    persist()
  }

  function clearCompleted() {
    // 清除已完成、失败、历史恢复的任务
    tasks.value = tasks.value.filter(t => t.status !== 'done' && t.status !== 'failed' && !t.restored)
    const taskIds = new Set(tasks.value.map(t => t.id))
    for (const id of Object.keys(results.value)) {
      if (!taskIds.has(id)) delete results.value[id]
    }
    for (const id of Object.keys(errors.value)) {
      if (!taskIds.has(id)) delete errors.value[id]
    }
    if (currentTaskId.value && !taskIds.has(currentTaskId.value)) {
      currentTaskId.value = tasks.value[0]?.id || null
    }
    persist()
  }

  function clearSelected() {
    const selectedIds = new Set(tasks.value.filter(t => t.selected).map(t => t.id))
    if (!selectedIds.size) return
    tasks.value = tasks.value.filter(t => !selectedIds.has(t.id))
    for (const id of selectedIds) {
      delete results.value[id]
      delete errors.value[id]
    }
    if (currentTaskId.value && selectedIds.has(currentTaskId.value)) {
      currentTaskId.value = tasks.value[0]?.id || null
    }
    persist()
  }

  function setTaskStatus(taskId, status) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) task.status = status
    persist()
  }

  function setTaskSelection(taskId, selected) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) task.selected = selected
    persist()
  }

  function setAllSelection(selected) {
    tasks.value.forEach(t => {
      if (!t.restored && t.base64) t.selected = selected
    })
    persist()
  }

  function setCurrentTask(taskId) {
    currentTaskId.value = tasks.value.some(t => t.id === taskId) ? taskId : null
    persist()
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
    // 成功时清除错误
    delete errors.value[taskId]
    persist()
  }

  function getResult(taskId) {
    return results.value[taskId] || null
  }

  function setError(taskId, error) {
    errors.value[taskId] = error
    // 错误时清除结果
    delete results.value[taskId]
    persist()
  }

  function getError(taskId) {
    return errors.value[taskId] || null
  }

  return {
    tasks,
    currentTaskId,
    currentTask,
    isProcessing,
    results,
    errors,
    pendingCount,
    processingCount,
    doneCount,
    failedCount,
    selectedTasks,
    addFiles,
    removeTask,
    clearCompleted,
    clearSelected,
    setTaskStatus,
    setTaskSelection,
    setAllSelection,
    setCurrentTask,
    recognizeSingle,
    submitBatch,
    pollBatchStatus,
    setResult,
    getResult,
    setError,
    getError,
    restorePersisted,
    persist,
  }
})
