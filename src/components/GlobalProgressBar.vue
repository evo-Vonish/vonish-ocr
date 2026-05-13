<template>
  <div class="gpb-root" :class="{ expanded, collapsed: !expanded, empty: totalCount === 0 }">
    <!-- 收起态：单行摘要 -->
    <div class="gpb-bar" @click="totalCount > 0 && (expanded = !expanded)">
      <div class="gpb-summary">
        <span v-if="totalCount > 0" class="gpb-dot" :class="statusDotClass" aria-hidden="true"></span>
        <span class="gpb-label">
          <template v-if="totalCount === 0">证据队列为空</template>
          <template v-else-if="allDone">{{ t('progress_all_done') }}</template>
          <template v-else-if="activeCount">{{ t('progress_active', { done: doneCount, total: totalCount }) }}</template>
          <template v-else>{{ t('progress_queued', { total: totalCount }) }}</template>
        </span>
        <span class="gpb-chips">
          <span v-if="preprocessedCount" class="gpb-chip pre">{{ preprocessedCount }}</span>
          <span v-if="doneCount" class="gpb-chip done">{{ doneCount }}</span>
          <span v-if="processingCount" class="gpb-chip proc">{{ processingCount }}</span>
          <span v-if="failedCount" class="gpb-chip fail">{{ failedCount }}</span>
        </span>
      </div>

      <div v-if="totalCount > 0" class="gpb-ratio">
        <span class="gpb-fraction">{{ doneCount }}/{{ totalCount }}</span>
        <span class="gpb-caret">{{ expanded ? '▲' : '▼' }}</span>
      </div>
    </div>

    <!-- 展开态：详情 + 操作 -->
    <div v-if="expanded" class="gpb-detail">
      <div class="gpb-stats">
        <div class="gpb-stat">
          <span class="gpb-stat-num">{{ preprocessedCount }}</span>
          <span class="gpb-stat-label">预处理</span>
        </div>
        <div class="gpb-stat">
          <span class="gpb-stat-num">{{ doneCount }}</span>
          <span class="gpb-stat-label">已完成</span>
        </div>
        <div class="gpb-stat">
          <span class="gpb-stat-num proc">{{ processingCount }}</span>
          <span class="gpb-stat-label">处理中</span>
        </div>
        <div class="gpb-stat">
          <span class="gpb-stat-num">{{ pendingCount }}</span>
          <span class="gpb-stat-label">等待</span>
        </div>
        <div class="gpb-stat">
          <span class="gpb-stat-num fail">{{ failedCount }}</span>
          <span class="gpb-stat-label">失败</span>
        </div>
        <div class="gpb-stat">
          <span class="gpb-stat-num">{{ totalCount }}</span>
          <span class="gpb-stat-label">总数</span>
        </div>
      </div>

      <!-- 细进度条 -->
      <div class="gpb-track">
        <span
          class="gpb-track-fill done"
          :style="{ width: donePct + '%' }"
        ></span>
        <span
          v-if="processingPct"
          class="gpb-track-fill proc"
          :style="{ width: processingPct + '%' }"
        ></span>
        <span
          v-if="failedPct"
          class="gpb-track-fill fail"
          :style="{ width: failedPct + '%' }"
        ></span>
      </div>

      <div class="gpb-actions">
        <!-- 空队列：上传为主按钮 -->
        <button
          v-if="totalCount === 0"
          class="gpb-btn primary"
          type="button"
          @click.stop="hiddenFile?.click()"
        >上传文件</button>
        <!-- 全部完成：一键导出 -->
        <button
          v-else-if="allDone"
          class="gpb-btn primary"
          type="button"
          @click.stop="doExport"
        >一键导出</button>
        <!-- 有待处理且未在处理中：开始识别 -->
        <button
          v-else-if="pendingCount && !taskStore.isProcessing"
          class="gpb-btn primary"
          type="button"
          @click.stop="doStart"
        >开始识别</button>
        <!-- 有内容时始终显示上传 -->
        <button
          v-if="totalCount > 0"
          class="gpb-btn"
          type="button"
          @click.stop="hiddenFile?.click()"
        >上传</button>
        <!-- 有已完成项时显示清空 -->
        <button
          v-if="doneCount"
          class="gpb-btn danger"
          type="button"
          @click.stop="doClear"
        >清空已完成</button>
      </div>
      <input ref="hiddenFile" type="file" multiple accept="image/*,.pdf" hidden @change="onUpload" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { useConfigStore } from '../stores/configStore'
import { useFileUpload } from '../composables/useFileUpload'
import { exportBatch } from '../utils/exporters'
import { showToast } from '../composables/useToast'
import { ocrBatch, createBatchWebSocket, getBatchResults, getBatchStatus, parseApiError } from '../api/tauri_ipc'
import { t } from '../i18n'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const { addFiles } = useFileUpload()
const expanded = ref(false)
const hiddenFile = ref(null)
let ws = null

const totalCount = computed(() => taskStore.tasks.length)
const hasTasks = computed(() => totalCount.value > 0)
const doneCount = computed(() => taskStore.tasks.filter(t => t.status === 'done').length)
const failedCount = computed(() => taskStore.tasks.filter(t => t.status === 'failed').length)
const processingCount = computed(() => taskStore.tasks.filter(t => t.status === 'processing' || t.status === 'refining' || t.status === 'preprocessing').length)
const pendingCount = computed(() => taskStore.tasks.filter(t => t.status === 'pending' || t.status === 'queued').length)
const preprocessedCount = computed(() => doneCount.value + failedCount.value + processingCount.value)
const activeCount = computed(() => processingCount.value + pendingCount.value + preprocessedCount.value)
const allDone = computed(() => totalCount.value > 0 && doneCount.value + failedCount.value === totalCount.value && processingCount.value === 0)

const donePct = computed(() => totalCount.value ? Math.round((doneCount.value / totalCount.value) * 100) : 0)
const processingPct = computed(() => totalCount.value ? Math.round((processingCount.value / totalCount.value) * 100) : 0)
const failedPct = computed(() => totalCount.value ? Math.round((failedCount.value / totalCount.value) * 100) : 0)

const statusDotClass = computed(() => {
  if (processingCount.value) return 'busy'
  if (allDone.value && failedCount.value === 0) return 'ok'
  if (allDone.value && failedCount.value > 0) return 'warn'
  return ''
})

function onUpload(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function doClear() {
  const ids = taskStore.tasks.filter(t => t.status === 'done').map(t => t.id)
  ids.forEach(id => taskStore.removeTask(id))
  showToast({ type: 'info', message: `已清空 ${ids.length} 条`, duration: 1600 })
}

async function doExport() {
  const items = taskStore.tasks
    .filter(t => t.status === 'done' && taskStore.getResult(t.id)?.text)
    .map(t => ({ task: t, result: taskStore.getResult(t.id) }))
  if (!items.length) return
  await exportBatch(items, { mode: 'polished', format: 'md', output: 'zip' })
  showToast({ type: 'success', message: t('toast_saved_selected').replace('{count}', items.length), duration: 1800 })
}

async function doStart() {
  const runnable = taskStore.tasks.filter(t => t.selected && t.base64 && !t.restored)
  if (!runnable.length) {
    showToast({ type: 'error', message: t('queue_empty_ghost'), duration: 2000 })
    return
  }
  runnable.forEach(f => taskStore.setTaskStatus(f.id, 'queued'))

  if (runnable.length === 1) {
    taskStore.setCurrentTask(runnable[0].id)
    taskStore.setTaskStatus(runnable[0].id, 'processing')
    try {
      const result = await taskStore.recognizeSingle(runnable[0].base64)
      taskStore.setResult(runnable[0].id, result)
      taskStore.setTaskStatus(runnable[0].id, 'done')
    } catch (e) {
      taskStore.setTaskStatus(runnable[0].id, 'failed')
      taskStore.setError(runnable[0].id, parseApiError(e, '识别失败'))
    }
    return
  }

  taskStore.isProcessing = true
  runnable.forEach(f => taskStore.setTaskStatus(f.id, 'processing'))
  try {
    const { task_id } = await ocrBatch(runnable.map(f => f.base64), {
      model: configStore.config.ocr_model || 'rapidocr-mobile-cn',
      output_mode: configStore.config.output_mode || 'smart',
    })
    const doneWs = new Promise(resolve => {
      ws = createBatchWebSocket(task_id, msg => {
        if (msg.type !== 'progress') return
        if (typeof msg.index === 'number' && runnable[msg.index]) {
          const t = runnable[msg.index]
          if (msg.result && !msg.result.error) {
            taskStore.setResult(t.id, msg.result)
            taskStore.setTaskStatus(t.id, 'done')
          } else if (msg.error || msg.result?.error) {
            taskStore.setError(t.id, { code: 'OCR_ENGINE_ERROR', message: msg.error || msg.result?.error })
            taskStore.setTaskStatus(t.id, 'failed')
          }
        }
        if (msg.total > 0 && msg.completed >= msg.total) resolve(true)
      })
    })
    await Promise.race([doneWs, pollBatch(task_id)])
    const br = await getBatchResults(task_id).catch(() => null)
    br?.results?.forEach((r, i) => {
      if (!runnable[i]) return
      if (r && !r.error) { taskStore.setResult(runnable[i].id, r); taskStore.setTaskStatus(runnable[i].id, 'done') }
      else { taskStore.setError(runnable[i].id, { code: 'OCR_ENGINE_ERROR', message: r?.error || '' }); taskStore.setTaskStatus(runnable[i].id, 'failed') }
    })
  } catch (e) {
    runnable.forEach(f => {
      if (!taskStore.getResult(f.id)) taskStore.setTaskStatus(f.id, 'failed')
    })
    showToast({ type: 'error', message: parseApiError(e, '批量识别失败').message, duration: 4000 })
  } finally {
    taskStore.isProcessing = false
    ws?.close()
    ws = null
  }
}

async function pollBatch(taskId) {
  for (let i = 0; i < 360; i++) {
    const s = await getBatchStatus(taskId).catch(() => null)
    if (s?.status === 'completed' || s?.status === 'cancelled') return s
    await new Promise(r => setTimeout(r, 800))
  }
  throw new Error('timeout')
}
</script>

<style scoped>
.gpb-root.empty .gpb-bar {
  cursor: default;
}

.gpb-root {
  position: fixed;
  bottom: var(--layout-gap);
  left: 50%;
  transform: translateX(-50%);
  z-index: 90;
  min-width: min(480px, calc(100vw - 64px));
  max-width: min(640px, calc(100vw - 48px));
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  box-shadow: 0 -2px 24px rgba(0,0,0,0.3);
  transition: border-color 0.2s;
}

/* ── 收起栏 ── */
.gpb-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--s4);
  height: 40px;
  cursor: pointer;
  user-select: none;
}

.gpb-bar:hover { border-color: var(--v-border-strong); }

.gpb-summary {
  display: flex;
  align-items: center;
  gap: var(--s2);
  min-width: 0;
}

.gpb-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--v-text-faint);
  flex-shrink: 0;
}

.gpb-dot.busy {
  background: var(--v-accent);
  animation: gpb-dot-pulse 1.2s ease-in-out infinite;
}

.gpb-dot.ok { background: var(--v-accent); }
.gpb-dot.warn { background: var(--v-format); }

@keyframes gpb-dot-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.gpb-label {
  font-size: var(--fs-caption);
  color: var(--v-text);
  white-space: nowrap;
}

.gpb-chips {
  display: flex;
  gap: 4px;
  margin-left: var(--s2);
}

.gpb-chip {
  padding: 0 6px;
  border-radius: var(--r1);
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 18px;
  color: var(--v-text-muted);
  background: var(--v-panel);
}

.gpb-chip.done { color: var(--v-accent); }
.gpb-chip.proc { color: var(--v-accent); }
.gpb-chip.fail { color: var(--v-error); }

.gpb-ratio {
  display: flex;
  align-items: center;
  gap: var(--s2);
  flex-shrink: 0;
}

.gpb-fraction {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
}

.gpb-caret {
  font-size: 9px;
  color: var(--v-text-faint);
}

/* ── 展开详情 ── */
.gpb-detail {
  padding: 0 var(--s4) var(--s4);
  display: flex;
  flex-direction: column;
  gap: var(--s3);
  animation: gpb-expand 0.2s ease;
}

@keyframes gpb-expand {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 200px; }
}

.gpb-stats {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--s2);
}

.gpb-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--s2) 0;
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
}

.gpb-stat-num {
  font-family: var(--font-mono);
  font-size: var(--fs-h2);
  color: var(--v-text);
  line-height: 1;
}

.gpb-stat-num.proc { color: var(--v-accent); }
.gpb-stat-num.fail { color: var(--v-error); }

.gpb-stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--v-text-faint);
  letter-spacing: 0.04em;
}

/* 进度条 */
.gpb-track {
  height: 4px;
  background: var(--v-bg);
  border-radius: 2px;
  overflow: hidden;
  display: flex;
}

.gpb-track-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.gpb-track-fill.done { background: var(--v-accent); }
.gpb-track-fill.proc { background: var(--v-accent); animation: gpb-track-pulse 1s ease-in-out infinite; }
.gpb-track-fill.fail { background: var(--v-error); }

@keyframes gpb-track-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 操作按钮 */
.gpb-actions {
  display: flex;
  gap: var(--s1);
}

.gpb-btn {
  flex: 1;
  min-height: 32px;
  padding: 0 var(--s2);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: transparent;
  color: var(--v-text);
  font-size: var(--fs-caption);
  cursor: pointer;
  transition: border-color 0.15s;
}

.gpb-btn:hover { border-color: var(--v-border-strong); }

.gpb-btn.primary {
  background: var(--v-accent);
  border-color: var(--v-accent);
  color: var(--v-coal);
  font-weight: var(--fw-semibold);
}

.gpb-btn.danger {
  border-color: var(--v-error);
  color: var(--v-error);
}

/* ── 窄屏 ── */
@media (max-width: 600px) {
  .gpb-root {
    min-width: calc(100vw - 32px);
    left: var(--s4);
    transform: none;
  }

  .gpb-stats {
    grid-template-columns: repeat(3, 1fr);
  }

  .gpb-chips {
    display: none;
  }
}
</style>
