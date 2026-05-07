<template>
  <section style="min-height: 100%; display: flex; flex-direction: column; gap: var(--s4);">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: var(--s4);">
      <div style="min-width: 0;">
        <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em;">{{ t('ocr_result_title') }}</div>
        <div class="v-display" style="font-size: var(--fs-h1); word-break: break-word;">{{ currentName }}</div>
      </div>
      <nav class="v-state-tabs ocr-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="v-state-tab"
          :class="{ 'is-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ t(tab.labelKey) }}
        </button>
      </nav>
    </div>

    <div v-if="isLoading" class="v-pipeline" style="margin-bottom: var(--s1);">
      <div
        v-for="step in pipelineSteps"
        :key="step.key"
        class="v-pipeline-node"
        :class="{ 'is-done': step.done, 'is-current': step.current }"
      >
        <span class="v-pipeline-dot"></span>
        <span>{{ step.label }}</span>
      </div>
    </div>

    <div v-if="displayError" class="v-result-col" style="min-height: 420px; display: grid; place-items: center; border-color: var(--v-error); background: var(--v-error-dim);">
      <div style="text-align: center; max-width: 640px;">
        <div class="v-micro">OCR ERROR</div>
        <div class="v-title" style="font-size: var(--fs-h2); margin-top: var(--s2); color: var(--v-error);">{{ t('ocr_error_title') }}</div>
        <div class="v-body-text" style="margin-top: var(--s3); color: var(--v-text);">{{ displayError.message }}</div>
        <div class="v-small" style="margin-top: var(--s3);">{{ errorHint(displayError.code) }}</div>
        <div class="v-state-tabs error-actions" style="margin-top: var(--s5); height: auto; flex-wrap: wrap; justify-content: center;">
          <button class="v-state-tab" type="button" :disabled="!taskStore.currentTask?.base64" @click="retryOcr">{{ t('btn_retry') }}</button>
          <button class="v-state-tab" type="button" @click="showErrorDetail = true">{{ t('btn_detail') }}</button>
          <button class="v-state-tab" type="button" @click="copyError">{{ t('btn_copy') }}</button>
          <button class="v-state-tab" type="button" @click="reportError">{{ t('btn_report') }}</button>
          <button class="v-export-btn error-export" type="button" @click="exportOriginal">{{ t('btn_export') }}</button>
        </div>
      </div>
    </div>

    <div v-else-if="isLoading" class="v-empty-state" style="min-height: 420px; background: transparent;">
      <div class="v-preview-stage">
        <span class="v-fake-doc-line" style="position: absolute; left: var(--s6); top: var(--s6); width: 70%;"></span>
        <span class="v-fake-doc-line" style="position: absolute; left: var(--s6); top: calc(var(--s6) + var(--s5)); width: 56%;"></span>
        <span class="v-fake-doc-line" style="position: absolute; left: var(--s6); top: calc(var(--s6) + var(--s10)); width: 42%;"></span>
        <span class="v-scan-line"></span>
      </div>
    </div>

    <div v-else-if="!rawResult" class="v-empty-state" style="min-height: 420px; background: transparent;">
      <div class="v-dropzone">
        <div>
          <div class="v-empty-title">{{ t('empty_state_title') }}</div>
          <div class="v-empty-subtitle">{{ t('empty_state_sub') }}</div>
          <div class="v-local-idle">{{ t('empty_state_local') }}</div>
        </div>
      </div>
    </div>

    <div v-else style="min-height: 0; flex: 1; overflow: auto;">
      <div v-if="activeTab === 'raw'" class="v-result-col" style="min-height: 100%;">
        <div class="v-result-label">RAW OCR</div>
        <pre class="v-ocr-text" style="margin: 0; white-space: pre-wrap; word-break: break-word;">{{ displayResult.text || t('ocr_no_result') }}</pre>
      </div>

      <div v-if="activeTab === 'refined'" class="v-result-col" style="min-height: 100%;">
        <div style="margin-bottom: var(--s3);">
          <div class="v-result-label" style="margin-bottom: var(--s1);">{{ t('ai_refined_title') }}</div>
          <div v-if="displayResult.aiError" class="v-small" style="color: var(--v-error);">{{ t('ai_refine_auto_error') }}: {{ displayResult.aiError.message }}</div>
        </div>
        <div v-if="streamStatus === 'streaming'" class="v-mono-accent" style="margin-bottom: var(--s3);">{{ t('ai_streaming') }}</div>
        <pre class="v-ocr-text" style="margin: 0; white-space: pre-wrap; word-break: break-word;">{{ streamedText || displayResult.polished || t('ai_empty') }}</pre>
        <div v-if="streamStatus === 'error'" class="v-small" style="margin-top: var(--s3); color: var(--v-error);">{{ t('ai_refine_failed') }}: {{ aiStream.error.value?.message || t('unknown_error') }}</div>
        <div v-if="streamStatus === 'interrupted'" class="v-small" style="margin-top: var(--s3);">{{ t('ai_interrupted') }}</div>
      </div>

      <div v-if="activeTab === 'diff'" class="v-result-col v-diff-panel" style="min-height: 100%;">
        <div class="v-result-label">DIFF RECORD</div>
        <div v-if="!displayResult.diff.length" class="v-small">{{ t('diff_empty') }}</div>
        <div v-else class="v-diff-list">
          <div v-for="(item, index) in displayResult.diff" :key="index" class="v-diff-line">
            <span class="v-diff-from v-delete-mark">{{ item.original || '-' }}</span>
            <span class="v-diff-arrow">-&gt;</span>
            <span class="v-diff-to v-insert-mark">{{ item.revised || item.fixed || '-' }}</span>
            <span v-if="item.reason" class="v-caption" style="margin-left: var(--s3);">{{ item.reason }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showErrorDetail" class="error-modal" @click="showErrorDetail = false">
      <div class="v-panel error-modal-panel" role="dialog" aria-modal="true" @click.stop>
        <div style="display: flex; justify-content: space-between; gap: var(--s3); align-items: flex-start;">
          <div>
            <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em;">{{ t('error_detail_title') }}</div>
            <div class="v-title" style="font-size: var(--fs-h2); margin-top: var(--s1);">{{ t('ocr_error_title') }}</div>
          </div>
          <button class="v-state-tab" type="button" @click="showErrorDetail = false">{{ t('btn_close_detail') }}</button>
        </div>
        <div class="error-detail-grid">
          <span>{{ t('error_detail_file') }}</span><strong>{{ taskStore.currentTask?.name || t('no_file_selected') }}</strong>
          <span>{{ t('error_detail_status') }}</span><strong>{{ taskStore.currentTask?.status || '--' }}</strong>
          <span>{{ t('error_detail_code') }}</span><strong>{{ displayError.code || 'UNKNOWN' }}</strong>
          <span>{{ t('error_detail_message') }}</span><strong>{{ displayError.message }}</strong>
        </div>
        <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em; margin-top: var(--s4);">{{ t('error_detail_payload') }}</div>
        <pre class="error-detail-json">{{ errorDetailJson }}</pre>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { useAIStream } from '../composables/useAIStream'
import { showToast } from '../composables/useToast'
import { t } from '../i18n'

const taskStore = useTaskStore()
const aiStream = useAIStream()

const tabs = [
  { key: 'raw', labelKey: 'tab_raw' },
  { key: 'refined', labelKey: 'tab_refined' },
  { key: 'diff', labelKey: 'tab_diff' },
]

const stageOrder = ['scene_classify', 'deskew', 'preprocess', 'ocr', 'ai_refine', 'diff', 'complete']
const activeTab = ref('raw')
const showErrorDetail = ref(false)

const currentName = computed(() => taskStore.currentTask?.name || t('no_file_selected'))
const rawResult = computed(() => taskStore.currentTask ? taskStore.getResult(taskStore.currentTask.id) : null)
const displayError = computed(() => taskStore.currentTask ? taskStore.getError(taskStore.currentTask.id) : null)
const streamStatus = computed(() => aiStream.status.value)
const streamedText = computed(() => aiStream.text.value)

const isLoading = computed(() => {
  const task = taskStore.currentTask
  return !!task && (task.status === 'processing' || task.status === 'queued') && !rawResult.value
})

const pipelineSteps = computed(() => {
  const current = taskStore.pipelineStage || (isLoading.value ? 'ocr' : 'idle')
  const currentIndex = stageOrder.indexOf(current)
  return [
    { key: 'scene_classify', label: t('pipeline_scene') },
    { key: 'deskew', label: t('pipeline_deskew') },
    { key: 'preprocess', label: t('pipeline_preprocess') },
    { key: 'ocr', label: t('pipeline_ocr') },
    { key: 'ai_refine', label: t('pipeline_refine') },
    { key: 'diff', label: t('pipeline_diff') },
    { key: 'complete', label: t('pipeline_done') },
  ].map((step) => {
    const index = stageOrder.indexOf(step.key)
    return {
      ...step,
      done: currentIndex > index || current === 'complete',
      current: current === step.key || (current === 'idle' && step.key === 'ocr'),
    }
  })
})

const displayResult = computed(() => {
  const result = rawResult.value || {}
  const ai = result.ai || {}
  return {
    text: result.text || '',
    polished: ai.polished || result.refined_text || '',
    diff: ai.diff || result.diff || [],
    aiError: ai.error || null,
  }
})

function errorHint(code) {
  const hints = {
    MODEL_NOT_LOADED: 'error_hint_model_not_loaded',
    MODEL_LOAD_ERROR: 'error_hint_model_load_error',
    OCR_ENGINE_ERROR: 'error_hint_ocr_engine',
    AI_REFINER_FAILED: 'error_hint_ai_refiner',
    AI_ALL_PROVIDERS_FAILED: 'error_hint_ai_all_failed',
    INVALID_IMAGE: 'error_hint_invalid_image',
    MISSING_IMAGE: 'error_hint_missing_image',
    BATCH_TOO_LARGE: 'error_hint_batch_too_large',
  }
  return t(hints[code] || 'error_hint_default')
}

const errorDetailJson = computed(() => JSON.stringify({
  file: taskStore.currentTask?.name || null,
  taskId: taskStore.currentTask?.id || null,
  status: taskStore.currentTask?.status || null,
  model: rawResult.value?.model || null,
  error: displayError.value,
}, null, 2))

async function retryOcr() {
  const task = taskStore.currentTask
  if (!task?.base64) return
  taskStore.setTaskStatus(task.id, 'processing')
  try {
    const result = await taskStore.recognizeSingle(task.base64)
    taskStore.setResult(task.id, result)
    taskStore.setTaskStatus(task.id, 'done')
  } catch (error) {
    taskStore.setError(task.id, { code: error?.code || 'UNKNOWN', message: error?.message || t('ocr_error_sub') })
    taskStore.setTaskStatus(task.id, 'failed')
  }
}

async function copyError() {
  try {
    await navigator.clipboard.writeText(errorDetailJson.value)
    showToast({ type: 'success', message: t('toast_copied'), duration: 1800 })
  } catch (_) {
    showToast({ type: 'error', message: t('toast_copy_failed'), duration: 2400 })
  }
}

async function reportError() {
  await copyError()
  showErrorDetail.value = true
}

async function exportOriginal() {
  const text = rawResult.value?.text || errorDetailJson.value
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${taskStore.currentTask?.name || 'ocr-error'}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function startRefine() {
  const result = rawResult.value
  const taskId = taskStore.currentTask?.id
  if (!result || !taskId) return
  activeTab.value = 'refined'
  await aiStream.start({
    text: result.text || '',
    scene_type: result.scene || 'printed_document',
    confidence: result.confidence || 0,
  })
  const finalResult = aiStream.providerResult.value
  if (finalResult) {
    taskStore.setResult(taskId, {
      ...result,
      ai: {
        ...(result.ai || {}),
        ...finalResult,
      },
    })
  }
}

function stopRefine() {
  aiStream.stop()
}
</script>

<style scoped>
.ocr-tabs {
  min-width: 300px;
  height: auto;
  justify-content: flex-end;
  flex-wrap: nowrap;
}

.ocr-tabs .v-state-tab {
  min-width: 92px;
  height: 40px;
  padding-inline: var(--s4);
  font-size: var(--fs-caption);
}

.v-diff-panel {
  font-family: var(--font-body);
}

.v-diff-list {
  gap: var(--s3);
}

.v-diff-line {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  line-height: 1.85;
}

.v-diff-arrow,
.v-diff-line .v-caption {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.error-actions .v-state-tab,
.error-actions .v-export-btn {
  min-width: 88px;
  height: 36px;
}

.error-export {
  width: auto;
  padding-inline: var(--s4);
}

.error-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: var(--s6);
  background: color-mix(in srgb, var(--v-bg) 84%, transparent);
}

.error-modal-panel {
  width: min(760px, calc(100vw - var(--s8)));
  max-height: calc(100vh - var(--s8));
  overflow: auto;
  padding: var(--s5);
  border-radius: var(--r4);
}

.error-detail-grid {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: var(--s2) var(--s3);
  margin-top: var(--s4);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.error-detail-grid span {
  color: var(--v-text-muted);
}

.error-detail-grid strong {
  color: var(--v-text);
  min-width: 0;
  word-break: break-word;
}

.error-detail-json {
  margin-top: var(--s2);
  padding: var(--s3);
  max-height: 260px;
  overflow: auto;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .ocr-tabs {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .ocr-tabs .v-state-tab {
    flex: 1 1 120px;
  }
}
</style>
