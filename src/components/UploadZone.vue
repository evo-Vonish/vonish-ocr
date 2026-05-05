<template>
  <section v-if="variant === 'dropzone'" class="workbench-upload">
    <div
      class="drop-area"
      :class="{ active: isDragging, processing: taskStore.isProcessing }"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <input ref="fileInput" type="file" multiple accept="image/*" @change="onFileSelect" hidden />
      <div v-if="taskStore.isProcessing" class="preview-stage">
        <div class="paper-sheet">
          <span class="doc-line wide"></span>
          <span class="doc-line"></span>
          <span class="doc-line short"></span>
          <span class="doc-crease"></span>
          <span class="v-scan-line"></span>
        </div>
        <div class="pipeline">
          <div class="pipeline-node is-done"><span></span>LOAD IMAGE</div>
          <div class="pipeline-node is-current"><span></span>LOCAL OCR</div>
          <div class="pipeline-node"><span></span>AUDIT RESULT</div>
        </div>
      </div>
      <div v-else class="empty-copy">
        <div class="empty-title v-display">放入证据文件</div>
        <div class="empty-subtitle">JPG / PNG / WEBP / BMP，单次最多 200 张，本地优先识别。</div>
        <div class="local-idle">LOCAL HELD · DROP OR CLICK</div>
      </div>
    </div>
  </section>

  <section v-else class="queue-rail">
    <div class="rail-head">
      <div>
        <div class="rail-kicker">EVIDENCE QUEUE</div>
        <div class="rail-title v-title">证据队列</div>
      </div>
      <span class="queue-count">{{ taskStore.tasks.length.toString().padStart(2, '0') }}</span>
    </div>

    <div v-if="batchProgress.total > 0" class="batch-panel">
      <div class="batch-row">
        <span>OCR BATCH</span>
        <span class="progress-value">{{ batchProgress.completed }} / {{ batchProgress.total }}</span>
      </div>
      <div class="v-progress">
        <div class="v-progress-fill" :style="{ width: (batchProgress.completed / batchProgress.total * 100) + '%' }"></div>
      </div>
      <div class="batch-row muted">
        <span>{{ batchProgress.speed > 0 ? `${batchProgress.speed.toFixed(1)} / SEC` : batchProgress.status.toUpperCase() }}</span>
        <button v-if="batchProgress.status === 'processing'" class="text-btn danger" type="button" @click="cancelBatch">取消</button>
      </div>
    </div>

    <div class="queue-actions">
      <label class="check-all">
        <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
        <span>全选</span>
      </label>
      <div class="action-btns">
        <button class="text-btn" type="button"
                :disabled="!hasSelection || batchSave.isRunning"
                @click="saveSelected">
          保存选中
        </button>
        <button class="text-btn danger" type="button"
                :disabled="!hasSelection"
                @click="clearSelected">
          清除选中
        </button>
      </div>
    </div>

    <div class="queue-command-row">
      <button class="start-btn" type="button" @click="startOCR" :disabled="!selectedFiles.length || taskStore.isProcessing">
        {{ taskStore.isProcessing ? '本地识别中' : `开始识别 ${selectedFiles.length}` }}
      </button>
    </div>

    <div v-if="taskStore.tasks.length" class="upload-list">
      <button
        v-for="file in taskStore.tasks"
        :key="file.id"
        type="button"
        class="upload-row"
        :class="[file.status, { active: taskStore.currentTaskId === file.id }]"
        @click="selectFile(file)"
      >
        <input
          type="checkbox"
          :checked="file.selected"
          :disabled="file.restored || !file.base64"
          @change.stop="taskStore.setTaskSelection(file.id, $event.target.checked)"
          @click.stop
        />
        <img v-if="file.thumb" :src="file.thumb" class="thumb" alt="" />
        <span v-else class="thumb placeholder">OCR</span>
        <span class="file-copy">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-meta">{{ formatSize(file.size) }} · {{ statusText(file.status) }}<span v-if="file.restored"> · 历史</span></span>
        </span>
      </button>
    </div>
    <div v-else class="queue-empty">
      <span class="empty-line"></span>
      <span>等待文件进入证据桌</span>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { ocrBatch, createBatchWebSocket, cancelBatch as apiCancelBatch, getBatchResults, parseApiError } from '../api/tauri_ipc'
import { showToast } from '../composables/useToast'
import { notifyBatchComplete, notifyBatchFailed } from '../composables/useNotify'
import { useConfigStore } from '../stores/configStore'
import { exportBatch } from '../utils/exporters'

defineProps({
  variant: {
    type: String,
    default: 'queue',
  },
})

const taskStore = useTaskStore()
const configStore = useConfigStore()
const fileInput = ref(null)
const isDragging = ref(false)

const selectedFiles = computed(() => taskStore.tasks.filter(f => f.selected && f.base64 && !f.restored))
const completedItems = computed(() => taskStore.tasks
  .map(task => ({ task, result: taskStore.getResult(task.id) }))
  .filter(item => item.result?.text))
const selectedCompletedItems = computed(() => taskStore.tasks
  .filter(t => t.selected)
  .map(task => ({ task, result: taskStore.getResult(task.id) }))
  .filter(item => item.result?.text))

const isAllSelected = computed(() => {
  const selectable = taskStore.tasks.filter(t => !t.restored && t.base64)
  if (!selectable.length) return false
  return selectable.every(t => t.selected)
})

const hasSelection = computed(() => taskStore.tasks.some(t => t.selected))

const batchSave = reactive({
  format: 'md',
  mode: 'polished',
  output: 'zip',
  isRunning: false,
  done: 0,
  total: 0,
})

const batchProgress = reactive({
  taskId: null,
  total: 0,
  completed: 0,
  status: '',
  speed: 0,
  startTime: 0,
})
let ws = null

onMounted(() => {
  window.addEventListener('keydown', handleBatchSaveShortcut)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleBatchSaveShortcut)
})

function handleBatchSaveShortcut(event) {
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 's') {
    event.preventDefault()
    saveSelected()
  }
}

function onDrop(e) {
  isDragging.value = false
  addFiles(e.dataTransfer.files)
}

function onFileSelect(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function addFiles(items) {
  const MAX_SIZE = 10 * 1024 * 1024
  for (const f of items) {
    if (!f.type.startsWith('image/')) continue
    if (f.size > MAX_SIZE) {
      showToast({ type: 'warning', message: `文件 "${f.name}" 过大，请压缩后重新上传。最大 10MB。`, duration: 5000 })
      continue
    }
    const reader = new FileReader()
    reader.onload = (e) => {
      const [task] = taskStore.addFiles([{
        name: f.name,
        size: f.size,
        status: 'pending',
        selected: true,
        thumb: e.target.result,
        base64: e.target.result,
      }])
      taskStore.setCurrentTask(task.id)
    }
    reader.readAsDataURL(f)
  }
}

function toggleSelectAll() {
  taskStore.setAllSelection(!isAllSelected.value)
}

function clearSelected() {
  const count = taskStore.tasks.filter(t => t.selected).length
  if (!count) {
    showToast({ type: 'warning', message: '请先勾选要清除的任务', duration: 2000 })
    return
  }
  taskStore.clearSelected()
  showToast({ type: 'info', message: `已清除 ${count} 项`, duration: 2000 })
}

async function saveSelected() {
  const items = selectedCompletedItems.value
  if (!items.length) {
    showToast({ type: 'warning', message: '请先完成识别再保存', duration: 3000 })
    return
  }
  if (batchSave.isRunning) return
  batchSave.isRunning = true
  batchSave.done = 0
  batchSave.total = items.length
  try {
    await exportBatch(items, {
      format: batchSave.format,
      mode: batchSave.mode,
      output: batchSave.output,
      onProgress(done, total) {
        batchSave.done = done
        batchSave.total = total
      },
    })
    showToast({ type: 'success', message: `已保存 ${batchSave.total} 张识别结果`, duration: 2600 })
  } catch (e) {
    showToast({ type: 'error', message: e?.message || '批量保存失败', duration: 5000 })
  } finally {
    batchSave.isRunning = false
  }
}

function selectFile(file) {
  taskStore.setCurrentTask(file.id)
}

async function startOCR() {
  taskStore.tasks.forEach(f => {
    if (f.status === 'done' || f.status === 'failed') {
      taskStore.setTaskSelection(f.id, false)
    }
  })

  const selected = selectedFiles.value
  if (!selected.length) return

  selected.forEach(f => taskStore.setTaskStatus(f.id, 'queued'))

  if (selected.length === 1) {
    const file = selected[0]
    taskStore.setCurrentTask(file.id)
    taskStore.setTaskStatus(file.id, 'processing')
    try {
      const result = await taskStore.recognizeSingle(file.base64)
      taskStore.setResult(file.id, result)
      taskStore.setTaskStatus(file.id, 'done')
    } catch (e) {
      const err = parseApiError(e, '识别失败，请重试')
      taskStore.setTaskStatus(file.id, 'failed')
      taskStore.setError(file.id, err)
      showToast({ type: 'error', message: `${file.name}: ${err.message}`, duration: 5000 })
    }
    return
  }

  taskStore.isProcessing = true
  selected.forEach(f => taskStore.setTaskStatus(f.id, 'processing'))
  batchProgress.total = selected.length
  batchProgress.completed = 0
  batchProgress.status = 'processing'
  batchProgress.startTime = Date.now()
  batchProgress.speed = 0

  try {
    const { task_id } = await ocrBatch(selected.map(f => f.base64), {
      model: configStore.config.ocr_model || 'rapidocr-mobile-cn',
      output_mode: configStore.config.output_mode || 'smart',
      ai_refine_batch: !!configStore.config.batch_ai_refine,
    })
    batchProgress.taskId = task_id

    ws = await createBatchWebSocket(task_id, (msg) => {
      if (msg.type !== 'progress') return
      batchProgress.completed = msg.completed
      const elapsedSec = (Date.now() - batchProgress.startTime) / 1000
      batchProgress.speed = elapsedSec > 0 ? msg.completed / elapsedSec : 0

      if (typeof msg.index === 'number' && selected[msg.index]) {
        const target = selected[msg.index]
        if (msg.result && !msg.result.error) {
          taskStore.setResult(target.id, msg.result)
          taskStore.setTaskStatus(target.id, 'done')
        } else if (msg.error || msg.result?.error) {
          const message = msg.error || msg.result.error
          taskStore.setError(target.id, { code: 'OCR_ENGINE_ERROR', message })
          taskStore.setTaskStatus(target.id, 'failed')
        }
      }
    })

    await new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (batchProgress.completed >= batchProgress.total || batchProgress.status === 'cancelled') {
          clearInterval(checkInterval)
          resolve()
        }
      }, 500)
      setTimeout(() => {
        clearInterval(checkInterval)
        resolve()
      }, 60000)
    })

    try {
      const batchResult = await getBatchResults(batchProgress.taskId)
      if (batchResult?.results) {
        for (let i = 0; i < batchResult.results.length && i < selected.length; i++) {
          const r = batchResult.results[i]
          if (r && !r.error) {
            taskStore.setResult(selected[i].id, r)
            taskStore.setTaskStatus(selected[i].id, 'done')
          } else if (r?.error) {
            taskStore.setError(selected[i].id, { code: 'OCR_ENGINE_ERROR', message: r.error })
            taskStore.setTaskStatus(selected[i].id, 'failed')
          }
        }
      }
    } catch (e) {
      const err = parseApiError(e, '获取批量结果失败')
      showToast({ type: 'error', message: err.message, duration: 5000 })
    }

    if (batchProgress.status !== 'cancelled') {
      batchProgress.status = 'completed'
      if (configStore.config.notify_enabled) {
        const successCount = selected.filter(f => f.status === 'done').length
        const failCount = selected.filter(f => f.status === 'failed').length
        await notifyBatchComplete(successCount, failCount, selected.length)
      }
    }
  } catch (e) {
    const parsedError = parseApiError(e, '批量识别失败，请重试')
    selected.forEach(f => {
      taskStore.setTaskStatus(f.id, 'failed')
      taskStore.setError(f.id, parsedError)
    })
    showToast({ type: 'error', message: parsedError.message, duration: 6000 })
    if (configStore.config.notify_enabled) {
      await notifyBatchFailed(parsedError.message)
    }
  } finally {
    taskStore.isProcessing = false
    if (ws) {
      ws.close()
      ws = null
    }
    setTimeout(() => {
      if (batchProgress.status !== 'processing') {
        batchProgress.total = 0
        batchProgress.completed = 0
      }
    }, 3000)
  }
}

async function cancelBatch() {
  if (!batchProgress.taskId) return
  try {
    await apiCancelBatch(batchProgress.taskId)
    batchProgress.status = 'cancelled'
    if (ws) {
      ws.close()
      ws = null
    }
  } catch (e) {
    showToast({ type: 'error', message: '取消批量任务失败', duration: 3000 })
  }
}

function formatSize(b) {
  if (!b) return '--'
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / (1024 * 1024)).toFixed(1) + ' MB'
}

function statusText(s) {
  const map = { pending: '待处理', queued: '排队中', processing: '处理中', done: '已完成', failed: '失败' }
  return map[s] || s
}
</script>

<style scoped>
.workbench-upload {
  min-height: 100%;
}

.drop-area {
  min-height: calc(100vh - 220px);
  display: grid;
  place-items: center;
  background: var(--v-bg);
  border: 2px dashed var(--v-paper);
  border-radius: var(--r4);
  color: var(--v-text-muted);
  cursor: pointer;
  padding: var(--s8);
  transition:
    border-color var(--dur-base) var(--ease-cut),
    box-shadow var(--dur-base) var(--ease-cut),
    background-color var(--dur-base) var(--ease-cut);
}

.drop-area:hover,
.drop-area.active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
  background: color-mix(in srgb, var(--v-bg) 86%, var(--v-accent-dim) 14%);
}

.empty-copy {
  text-align: center;
}

.empty-title {
  text-align: center;
}

.empty-subtitle {
  margin-top: var(--s3);
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  text-align: center;
}

.local-idle {
  margin-top: var(--s6);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
}

.preview-stage {
  width: min(620px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px;
  gap: var(--s5);
  align-items: center;
}

.paper-sheet {
  position: relative;
  min-height: 320px;
  background: var(--v-paper);
  color: var(--v-coal);
  border-radius: var(--r3);
  overflow: hidden;
  padding: var(--s8);
}

.doc-line {
  display: block;
  height: 6px;
  width: 70%;
  margin-bottom: var(--s4);
  background: color-mix(in srgb, var(--v-coal) 54%, transparent);
  border-radius: var(--r1);
}

.doc-line.wide {
  width: 86%;
}

.doc-line.short {
  width: 44%;
}

.doc-crease {
  position: absolute;
  top: 15%;
  left: 58%;
  width: 1px;
  height: 70%;
  background: color-mix(in srgb, var(--v-coal) 36%, transparent);
  transform: rotate(-8deg);
}

.pipeline {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}

.pipeline-node {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  align-items: center;
  gap: var(--s2);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-text-muted);
}

.pipeline-node span {
  width: 8px;
  height: 8px;
  border: 1px solid var(--v-border);
  border-radius: 50%;
}

.pipeline-node.is-done,
.pipeline-node.is-current {
  color: var(--v-accent);
}

.pipeline-node.is-done span {
  background: var(--v-accent);
  border-color: var(--v-accent);
}

.pipeline-node.is-current span {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.queue-rail {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.rail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s3);
  margin-bottom: var(--s4);
}

.rail-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.rail-title {
  margin-top: var(--s1);
  font-size: var(--fs-h2);
}

.queue-count {
  font-family: var(--font-mono);
  font-size: 28px;
  line-height: 1;
  color: var(--v-accent);
}

.batch-panel {
  background: var(--v-panel-raised);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding: var(--s4);
  margin-bottom: var(--s4);
}

.batch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.batch-row.muted {
  margin-top: var(--s2);
}

.progress-value {
  color: var(--v-accent);
}

.queue-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s2);
  margin-bottom: var(--s3);
}

.check-all {
  display: inline-flex;
  align-items: center;
  gap: var(--s2);
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
  cursor: pointer;
}

input[type="checkbox"] {
  accent-color: var(--v-accent);
}

.text-btn {
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  cursor: pointer;
  font-size: var(--fs-caption);
  min-height: 28px;
  padding-inline: var(--s2);
}

.text-btn:hover {
  color: var(--v-text);
  border-color: var(--v-border-strong);
}

.text-btn.danger {
  color: var(--v-error);
  border-color: var(--v-error-dim);
}

.queue-command-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--s2);
}

.action-btns {
  display: flex;
  align-items: center;
  gap: var(--s2);
}

.start-btn,
.save-all-btn {
  width: 100%;
  height: 36px;
  border-radius: var(--r3);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  margin-bottom: var(--s4);
}

.start-btn {
  border: 0;
  background: var(--v-accent);
  color: var(--v-coal);
}

.save-all-btn {
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
}

.start-btn.compact {
  margin-bottom: 0;
}

.start-btn:disabled,
.save-all-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}



.upload-list {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  overflow: auto;
}

.upload-row {
  width: 100%;
  display: grid;
  grid-template-columns: 14px 42px minmax(0, 1fr);
  align-items: center;
  gap: var(--s2);
  text-align: left;
  background: var(--v-panel-raised);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s2);
  color: var(--v-text);
  cursor: pointer;
}

.upload-row:hover {
  border-color: var(--v-border-strong);
}

.upload-row.active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.upload-row.processing {
  border-color: var(--v-accent);
}

.upload-row.failed {
  border-color: var(--v-error);
  background: color-mix(in srgb, var(--v-error-dim) 50%, var(--v-panel) 50%);
}

.thumb {
  width: 42px;
  height: 42px;
  object-fit: cover;
  border-radius: var(--r2);
  border: 1px solid var(--v-border);
}

.thumb.placeholder {
  display: grid;
  place-items: center;
  background: var(--v-bg);
  color: var(--v-text-faint);
  font-family: var(--font-mono);
  font-size: 9px;
}

.file-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--fs-small);
  color: var(--v-text);
}

.file-meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-text-muted);
}

.queue-empty {
  flex: 1;
  min-height: 120px;
  display: grid;
  place-items: center;
  gap: var(--s3);
  color: var(--v-text-faint);
  font-size: var(--fs-caption);
  border: 1px dashed var(--v-border);
  border-radius: var(--r3);
}

.empty-line {
  width: 42px;
  height: 1px;
  background: var(--v-border-strong);
}

@media (max-width: 767px) {
  .queue-rail {
    min-height: 0;
  }

  .rail-head,
  .batch-panel,
  .queue-actions,
  .start-btn,
  .queue-empty {
    display: none;
  }

  .upload-list {
    flex-direction: row;
    overflow-x: auto;
  }

  .upload-row {
    min-width: 220px;
  }

  .drop-area {
    min-height: 360px;
    padding: var(--s5);
  }

  .preview-stage {
    grid-template-columns: 1fr;
  }
}
</style>
