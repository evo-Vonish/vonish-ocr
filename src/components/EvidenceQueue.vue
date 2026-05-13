<template>
  <section class="eq-root">
    <!-- 标题栏 + 动画计数 -->
    <div class="eq-head">
      <div>
        <div class="v-micro">{{ t('evidence_queue_title') }}</div>
        <div class="v-title eq-subtitle">{{ t('evidence_queue_subtitle') }}</div>
      </div>
      <span class="eq-count">
        <FlipCounter :value="taskStore.tasks.length" />
      </span>
    </div>

    <!-- 操作按钮组 -->
    <div class="eq-actions">
      <button class="eq-act-btn" type="button" :class="{ on: isAllSelected }" @click="toggleSelectAll">
        {{ t('btn_select_all') }}
      </button>
      <button class="eq-act-btn" type="button" :disabled="selectedDoneCount === 0" @click="saveSelected">
        {{ t('btn_save_selected') }}
      </button>
      <button class="eq-act-btn danger" type="button" :disabled="selectedCount === 0" @click="clearSelected">
        {{ t('btn_clear_selected') }}
      </button>
    </div>

    <!-- 启动 + 上传 行 -->
    <div class="eq-launch">
      <button class="eq-start-btn" type="button" :disabled="selectedRunnable.length === 0 || taskStore.isProcessing" @click="startOCR">
        {{ t('btn_start_ocr') }}
        <span class="eq-start-num">{{ selectedRunnable.length }}</span>
      </button>
      <button class="eq-upload-btn" type="button" @click="fileInput.click()">
        {{ t('btn_upload') }}
      </button>
      <input ref="fileInput" type="file" multiple accept="image/*,.pdf" hidden @change="onFileSelect" />
    </div>

    <!-- 队列列表 -->
    <div class="eq-list">
      <button
        v-for="file in sortedTasks"
        :key="file.id"
        type="button"
        class="eq-item"
        :class="{
          current: taskStore.currentTaskId === file.id,
          done: file.status === 'done',
          failed: file.status === 'failed',
          processing: file.status === 'processing',
          'is-muted': file.restored && !taskStore.getResult(file.id)
        }"
        @click="taskStore.setCurrentTask(file.id)"
      >
        <!-- 复选框 -->
        <span
          class="eq-cb"
          :class="{ on: file.selected }"
          @click.stop="taskStore.setTaskSelection(file.id, !file.selected)"
        >
          <svg v-if="file.selected" viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 6.5L4.5 9L10 3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none" />
          </svg>
        </span>

        <!-- 缩略图 -->
        <img v-if="file.thumb" :src="file.thumb" alt="" class="eq-thumb" />
        <span v-else class="eq-thumb-placeholder" aria-hidden="true">OCR</span>

        <!-- 文件名 + 元信息 -->
        <span class="eq-info">
          <span class="eq-name">{{ file.name }}</span>
          <span class="eq-meta">
            <span>{{ formatSize(file.size) }}</span>
            <span class="eq-sep">·</span>
            <span :class="statusClass(file.status)">{{ statusText(file.status) }}</span>
            <span v-if="file.restored" class="eq-sep">·</span>
            <span v-if="file.restored" class="eq-meta-tag">{{ t('queue_history') }}</span>
          </span>
        </span>

        <!-- 删除 -->
        <span class="eq-rm" :title="t('btn_remove_evidence')" @click.stop="taskStore.removeTask(file.id)">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
          </svg>
        </span>
      </button>
    </div>

    <!-- 底部拖拽区 -->
    <div
      class="eq-drop"
      :class="{ over: isDragging }"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <svg class="eq-drop-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 4V16M12 16L8 12M12 16L16 12M4 17V19C4 20 5 21 6 21H18C19 21 20 20 20 19V17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="eq-drop-text">{{ t('queue_empty_ghost') }}</span>
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
import FlipCounter from './FlipCounter.vue'
import { t } from '../i18n'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const { addFiles } = useFileUpload()
const fileInput = ref(null)
const isDragging = ref(false)
let ws = null

// ── 排序：已完成 → 失败 → 处理中 → 待处理 ──
const statusOrder = { done: 0, failed: 1, processing: 2, queued: 3, pending: 4, preprocessing: 5, refining: 6 }
const sortedTasks = computed(() =>
  [...taskStore.tasks].sort((a, b) => (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9))
)

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
        if (msg.total > 0 && msg.completed >= msg.total) resolve(true)
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

function statusClass(status) {
  return {
    done: 'eq-status-done',
    failed: 'eq-status-failed',
    processing: 'eq-status-processing',
    preprocessing: 'eq-status-processing',
    refining: 'eq-status-processing',
  }[status] || ''
}
</script>

<style scoped>
.eq-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ── 标题 + 动画计数 ── */
.eq-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s3);
  margin-bottom: var(--s3);
  flex-shrink: 0;
}

.eq-subtitle {
  font-size: var(--fs-h2);
  margin-top: var(--s1);
}

.eq-count {
  font-family: var(--font-mono);
  font-size: clamp(24px, 3vw, var(--fs-display));
  color: var(--v-accent);
  line-height: 1;
  flex-shrink: 0;
}

/* ── 操作按钮组 ── */
.eq-actions {
  display: flex;
  gap: var(--s1);
  margin-bottom: var(--s3);
  flex-shrink: 0;
}

.eq-act-btn {
  flex: 1;
  min-height: 36px;
  padding: 0 var(--s2);
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.eq-act-btn.on {
  border-color: var(--v-accent);
  color: var(--v-text);
}

.eq-act-btn.danger {
  color: var(--v-error);
  border-color: var(--v-border);
}

.eq-act-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.eq-act-btn:not(:disabled):hover { border-color: var(--v-border-strong); color: var(--v-text); }

/* ── 启动 + 上传 ── */
.eq-launch {
  display: flex;
  gap: var(--s2);
  margin-bottom: var(--s3);
  flex-shrink: 0;
}

.eq-start-btn {
  flex: 2;
  min-height: 40px;
  border: none;
  border-radius: var(--r3);
  background: var(--v-accent);
  color: var(--v-coal);
  font-weight: var(--fw-semibold);
  font-size: var(--fs-body);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--s2);
  transition: background 0.15s;
}

.eq-start-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.eq-start-btn:not(:disabled):hover { background: color-mix(in srgb, var(--v-accent) 80%, white); }

.eq-start-num {
  font-family: var(--font-mono);
  padding: 1px 6px;
  border-radius: var(--r1);
  background: color-mix(in srgb, var(--v-coal) 18%, transparent);
}

.eq-upload-btn {
  flex: 1;
  min-height: 40px;
  background: transparent;
  border: 1px solid var(--v-accent);
  border-radius: var(--r3);
  color: var(--v-accent);
  font-size: var(--fs-body);
  cursor: pointer;
  transition: background 0.15s;
}

.eq-upload-btn:hover { background: var(--v-accent-08); }

/* ── 队列列表 ── */
.eq-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--s1);
}

.eq-item {
  width: 100%;
  display: grid;
  grid-template-columns: 16px 40px minmax(0, 1fr) 24px;
  align-items: center;
  gap: clamp(6px, 1.2vw, var(--s3));
  padding: clamp(6px, 1vw, var(--s2));
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--r3);
  color: var(--v-text);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
  flex-shrink: 0;
}

/* 完成态：掌灯青边框 + 微光 */
.eq-item.done {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

/* 失败态：错误色边框 */
.eq-item.failed {
  border-color: var(--v-error);
}

/* 处理中：脉冲光 */
.eq-item.processing {
  border-color: var(--v-accent);
  animation: eq-processing-pulse 2s ease-in-out infinite;
}

@keyframes eq-processing-pulse {
  0%, 100% { box-shadow: var(--glow-soft); }
  50%      { box-shadow: var(--glow-active); }
}

/* 当前选中 */
.eq-item.current {
  border-color: var(--v-border-strong);
}

/* 悬浮：仅背景微调，不做位移 */
.eq-item:hover {
  background: var(--v-rail);
}

.eq-item.done:hover {
  background: var(--v-rail);
  box-shadow: var(--glow-active);
}

/* 复选框 */
.eq-cb {
  width: 16px; height: 16px;
  display: grid;
  place-items: center;
  border: 1px solid var(--v-border);
  border-radius: var(--r1);
  background: var(--v-bg);
  color: var(--v-accent);
  flex-shrink: 0;
}

.eq-cb.on { border-color: var(--v-accent); background: var(--v-accent-16); }

/* 缩略图 */
.eq-thumb {
  width: 40px; height: 40px;
  object-fit: cover;
  border: 1px solid var(--v-border);
  border-radius: var(--r1);
  flex-shrink: 0;
}

.eq-thumb-placeholder {
  width: 40px; height: 40px;
  display: grid;
  place-items: center;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r1);
  font-size: 9px;
  color: var(--v-text-faint);
  flex-shrink: 0;
}

/* 文件信息 */
.eq-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.eq-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--fs-small);
  color: var(--v-text);
}

.eq-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--v-text-muted);
  white-space: nowrap;
  overflow: hidden;
}

.eq-sep { color: var(--v-text-faint); }

.eq-status-done { color: var(--v-accent); }
.eq-status-failed { color: var(--v-error); }
.eq-status-processing { color: var(--v-accent); animation: eq-pulse-text 1s ease-in-out infinite; }

@keyframes eq-pulse-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.eq-meta-tag {
  padding: 0 4px;
  border: 1px solid var(--v-border);
  border-radius: var(--r1);
  font-size: 8px;
  letter-spacing: 0.06em;
}

/* 删除按钮 */
.eq-rm {
  width: 24px; height: 24px;
  display: grid;
  place-items: center;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text-muted);
  flex-shrink: 0;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.eq-rm:hover { border-color: var(--v-error); color: var(--v-error); }

.eq-rm svg { width: 12px; height: 12px; }

/* ── 底部拖拽区 ── */
.eq-drop {
  flex-shrink: 0;
  height: 72px;
  margin-top: var(--s3);
  padding: var(--s3);
  display: grid;
  place-items: center;
  gap: var(--s1);
  cursor: pointer;
  border: 1px dashed var(--v-border);
  border-radius: var(--r4);
  background: transparent;
  transition: border-color 0.15s, background 0.15s;
}

.eq-drop.over {
  border-color: var(--v-accent);
  background: var(--v-panel);
}

.eq-drop-icon {
  width: 22px; height: 22px;
  color: var(--v-text-muted);
}

.eq-drop-text {
  font-size: var(--fs-small);
  color: var(--v-text-muted);
}

/* ── 窄屏 ── */
@media (max-width: 767px) {
  .eq-item {
    grid-template-columns: 14px 32px minmax(0, 1fr) 20px;
    gap: 4px;
    padding: 4px;
  }

  .eq-thumb,
  .eq-thumb-placeholder { width: 32px; height: 32px; }

  .eq-cb { width: 14px; height: 14px; }

  .eq-name { font-size: 12px; }
  .eq-meta { font-size: 8px; gap: 2px; }
  .eq-rm { width: 20px; height: 20px; }
  .eq-rm svg { width: 10px; height: 10px; }

  .eq-act-btn { font-size: 11px; min-height: 32px; padding: 0 var(--s1); }
  .eq-start-btn { font-size: 13px; }
}
</style>
