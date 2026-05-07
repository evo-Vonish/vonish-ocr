<template>
  <section style="height: 100%; display: flex; flex-direction: column; min-height: 0;">
    <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: var(--s3); margin-bottom: var(--s3);">
      <div>
        <div class="v-micro">{{ t('evidence_queue_title') }}</div>
        <div class="v-title" style="font-size: var(--fs-h2); margin-top: var(--s1);">{{ t('evidence_queue_subtitle') }}</div>
      </div>
      <span class="v-mono-accent" style="font-size: var(--fs-display); line-height: 1;">
        <AnimatedCounter :value="taskStore.tasks.length" :pad="2" />
      </span>
    </div>

    <div class="v-state-tabs" style="height: auto; flex-wrap: wrap; margin-bottom: var(--s3);">
      <button class="v-state-tab" type="button" :class="{ 'is-active': isAllSelected }" style="flex: 1 1 calc(50% - var(--s2));" @click="toggleSelectAll">
        {{ t('btn_select_all') }}
      </button>
      <button class="v-state-tab" type="button" :class="{ 'is-active': selectedDoneCount > 0 }" :disabled="selectedDoneCount === 0" style="flex: 1 1 calc(50% - var(--s2));" @click="saveSelected">
        {{ t('btn_save_selected') }}
      </button>
      <button class="v-state-tab" type="button" :disabled="selectedCount === 0" style="flex: 1 1 100%; background: var(--v-error); color: var(--v-paper); border-color: var(--v-error);" @click="clearSelected">
        {{ t('btn_clear_selected') }}
      </button>
    </div>

    <div style="display: flex; gap: var(--s2); margin-bottom: var(--s3);">
      <button class="v-export-btn" type="button" :disabled="selectedRunnable.length === 0 || taskStore.isProcessing" style="flex: 2; height: 40px;" @click="startOCR">
        {{ t('btn_start_ocr') }} <span class="v-mono" style="color: var(--v-coal);">{{ selectedRunnable.length }}</span>
      </button>
      <button class="v-state-tab" type="button" style="flex: 1; height: 40px; border-color: var(--v-accent); color: var(--v-accent);" @click="fileInput.click()">
        {{ t('btn_upload') }}
      </button>
      <input ref="fileInput" type="file" multiple accept="image/*,.pdf" hidden @change="onFileSelect" />
    </div>

    <div class="v-model-list" style="min-height: 0; overflow: auto;">
      <button
        v-for="file in taskStore.tasks"
        :key="file.id"
        type="button"
        class="v-card"
        :class="{ 'is-active': taskStore.currentTaskId === file.id || file.selected, 'is-muted': file.restored && !taskStore.getResult(file.id) }"
        style="width: 100%; display: grid; grid-template-columns: 16px 40px minmax(0, 1fr) 24px; align-items: center; gap: var(--s3); text-align: left;"
        @click="taskStore.setCurrentTask(file.id)"
      >
        <span
          style="width: var(--s4); height: var(--s4); display: grid; place-items: center; border: 1px solid var(--v-border); border-radius: var(--r1); background: var(--v-bg); color: var(--v-accent);"
          :style="file.selected ? 'border-color: var(--v-accent); background: var(--v-accent-16);' : ''"
          @click.stop="taskStore.setTaskSelection(file.id, !file.selected)"
        >
          <svg v-if="file.selected" viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 6.5L4.5 9L10 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none" />
          </svg>
        </span>
        <img v-if="file.thumb" :src="file.thumb" alt="" style="width: 40px; height: 40px; object-fit: cover; border: 1px solid var(--v-border); border-radius: var(--r1);" />
        <span v-else style="width: 40px; height: 40px; display: grid; place-items: center; background: var(--v-bg); border: 1px solid var(--v-border); border-radius: var(--r1);" class="v-micro">OCR</span>
        <span style="min-width: 0;">
          <span class="v-card-title" style="display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ file.name }}</span>
          <span class="v-card-meta">{{ formatSize(file.size) }} · {{ statusText(file.status) }}<span v-if="file.restored"> · {{ t('queue_history') }}</span></span>
        </span>
        <span
          :title="t('btn_remove_evidence')"
          style="width: var(--s6); height: var(--s6); display: grid; place-items: center; border: 1px solid var(--v-border); border-radius: var(--r2); color: var(--v-text-muted);"
          @click.stop="taskStore.removeTask(file.id)"
        >
          <svg viewBox="0 0 12 12" aria-hidden="true" style="width: var(--s3); height: var(--s3);">
            <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
          </svg>
        </span>
      </button>
    </div>

    <div
      class="v-dropzone"
      style="width: 100%; height: 80px; min-height: 80px; margin-top: var(--s3); padding: var(--s3); display: grid; place-items: center; cursor: pointer;"
      :style="isDragging ? 'border: 1px solid var(--v-accent); background: var(--v-panel);' : ''"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <div style="display: grid; place-items: center; gap: var(--s1);">
        <svg class="v-model-icon" style="width: 24px; height: 24px; color: var(--v-text-muted);" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 4V16M12 16L8 12M12 16L16 12M4 17V19C4 20 5 21 6 21H18C19 21 20 20 20 19V17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div class="v-card-title" style="font-size: var(--fs-small); color: var(--v-text-muted);">{{ t('queue_empty_ghost') }}</div>
        <div class="v-caption">{{ t('queue_empty_sub') }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { useConfigStore } from '../stores/configStore'
import { ocrBatch, createBatchWebSocket, getBatchResults, getBatchStatus, parseApiError } from '../api/tauri_ipc'
import { showToast } from '../composables/useToast'
import { useFileUpload } from '../composables/useFileUpload'
import { exportBatch } from '../utils/exporters'
import AnimatedCounter from './AnimatedCounter.vue'
import { t } from '../i18n'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const { addFiles } = useFileUpload()
const fileInput = ref(null)
const isDragging = ref(false)
let ws = null

const selectedCount = computed(() => taskStore.tasks.filter(t => t.selected).length)
const selectedRunnable = computed(() => taskStore.tasks.filter(t => t.selected && t.base64 && !t.restored))
const selectedDone = computed(() => taskStore.tasks.filter(t => t.selected && taskStore.getResult(t.id)?.text))
const selectedDoneCount = computed(() => selectedDone.value.length)
const isAllSelected = computed(() => taskStore.tasks.length > 0 && taskStore.tasks.every(t => t.selected))

function toggleSelectAll() {
  const next = !isAllSelected.value
  taskStore.tasks.forEach(t => taskStore.setTaskSelection(t.id, next))
}

function onFileSelect(event) {
  addFiles(event.target.files)
  event.target.value = ''
}

function onDrop(event) {
  isDragging.value = false
  addFiles(event.dataTransfer.files)
}

async function saveSelected() {
  const items = selectedDone.value.map(task => ({ task, result: taskStore.getResult(task.id) }))
  if (!items.length) return
  await exportBatch(items, { mode: 'polished', format: 'md', output: 'zip' })
  showToast({ type: 'success', message: t('toast_saved_selected').replace('{count}', items.length), duration: 1800 })
}

function clearSelected() {
  if (!selectedCount.value) return
  taskStore.clearSelected()
  showToast({ type: 'info', message: t('toast_cleared_selected'), duration: 1600 })
}

async function startOCR() {
  const selected = selectedRunnable.value
  if (!selected.length) return
  selected.forEach(f => taskStore.setTaskStatus(f.id, 'queued'))

  if (selected.length === 1) {
    await recognizeOne(selected[0], taskStore.getPreprocessJob(selected[0].id) ? { preprocess_job_id: taskStore.getPreprocessJob(selected[0].id).job_id } : {})
    return
  }

  taskStore.isProcessing = true
  selected.forEach(f => taskStore.setTaskStatus(f.id, 'processing'))
  try {
    const { task_id } = await ocrBatch(selected.map(f => f.base64), {
      model: configStore.config.ocr_model || 'rapidocr-mobile-cn',
      output_mode: configStore.config.output_mode || 'smart',
    })
    const doneFromWs = new Promise((resolve) => {
      ws = createBatchWebSocket(task_id, (msg) => {
        if (msg.type !== 'progress') return
        if (typeof msg.index === 'number' && selected[msg.index]) {
          applyBatchItem(selected[msg.index], msg)
        }
        if (msg.total > 0 && msg.completed >= msg.total) {
          resolve(true)
        }
      })
    })
    const doneFromPoll = waitBatchDone(task_id)
    await Promise.race([doneFromWs, doneFromPoll])
    const batchResult = await waitBatchResults(task_id)
    batchResult?.results?.forEach((result, index) => {
      if (!selected[index]) return
      if (result && !result.error) {
        taskStore.setResult(selected[index].id, result)
        taskStore.setTaskStatus(selected[index].id, 'done')
      } else {
        taskStore.setError(selected[index].id, { code: 'OCR_ENGINE_ERROR', message: result?.error || t('ocr_error_sub') })
        taskStore.setTaskStatus(selected[index].id, 'failed')
      }
    })
  } catch (error) {
    const parsed = parseApiError(error, t('toast_batch_failed'))
    selected.forEach(f => {
      if (taskStore.getResult(f.id) || taskStore.getError(f.id)) return
      taskStore.setTaskStatus(f.id, 'failed')
      taskStore.setError(f.id, parsed)
    })
    showToast({ type: 'error', message: parsed.message, duration: 4000 })
  } finally {
    taskStore.isProcessing = false
    const socket = await Promise.resolve(ws).catch(() => null)
    socket?.close()
    ws = null
  }
}

function applyBatchItem(target, msg) {
  if (msg.result && !msg.result.error) {
    taskStore.setResult(target.id, msg.result)
    taskStore.setTaskStatus(target.id, 'done')
  } else if (msg.error || msg.result?.error) {
    taskStore.setError(target.id, { code: 'OCR_ENGINE_ERROR', message: msg.error || msg.result.error })
    taskStore.setTaskStatus(target.id, 'failed')
  }
}

async function waitBatchDone(taskId) {
  for (let i = 0; i < 360; i++) {
    const status = await getBatchStatus(taskId).catch(() => null)
    if (status?.status === 'completed' || status?.status === 'cancelled') return status
    await new Promise(resolve => setTimeout(resolve, 800))
  }
  throw new Error('Batch timeout')
}

async function waitBatchResults(taskId) {
  for (let i = 0; i < 20; i++) {
    const result = await getBatchResults(taskId).catch(() => null)
    if (result?.results) return result
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  return null
}

async function recognizeOne(file, options = {}) {
  taskStore.setCurrentTask(file.id)
  taskStore.setTaskStatus(file.id, 'processing')
  try {
    const result = await taskStore.recognizeSingle(file.base64, options)
    taskStore.setResult(file.id, result)
    taskStore.setTaskStatus(file.id, 'done')
  } catch (error) {
    const parsed = parseApiError(error, t('toast_ocr_failed'))
    taskStore.setTaskStatus(file.id, 'failed')
    taskStore.setError(file.id, parsed)
    showToast({ type: 'error', message: parsed.message, duration: 4000 })
  }
}

function formatSize(bytes) {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function statusText(status) {
  return ({
    pending: t('queue_waiting'),
    queued: t('queue_queued'),
    preprocessing: t('queue_preprocessing'),
    processing: t('queue_recognizing'),
    refining: t('queue_refining'),
    done: t('queue_complete'),
    failed: t('queue_failed'),
  })[status] || status
}
</script>
