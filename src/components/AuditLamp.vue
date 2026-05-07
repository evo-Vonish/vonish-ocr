<template>
  <section style="height: 100%; display: flex; flex-direction: column; min-height: 0;">
    <div class="v-review-head">
      <div>
        <div class="v-review-status">{{ reviewStatus }}</div>
        <div class="v-title" style="font-size: var(--fs-h2);">{{ t('audit_lamp_title') }}</div>
      </div>
      <div class="v-pipeline-dot" :style="hasResult || hasError ? 'background: var(--v-accent); border-color: var(--v-accent); box-shadow: var(--glow-soft);' : ''"></div>
    </div>

    <div class="v-review-section">
      <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: var(--s2);">{{ t('audit_current_case') }}</div>
      <div class="v-card-title">{{ taskStore.currentTask?.name || t('audit_no_file') }}</div>
      <div class="v-card-meta" style="margin-top: var(--s2);">{{ currentTaskMeta }}</div>
    </div>

    <div v-if="preprocessReview" class="v-review-section" style="margin-top: var(--s3);">
      <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: var(--s2);">{{ t('audit_preprocess') }}</div>
      <div v-if="preprocessReview.url || preprocessReview.originalUrl" style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s2); margin-bottom: var(--s3);">
        <img v-if="preprocessReview.originalUrl" :src="preprocessReview.originalUrl" alt="" style="width: 100%; height: 72px; object-fit: contain; background: var(--v-bg); border: 1px dashed var(--v-border); border-radius: var(--r2);" />
        <img v-if="preprocessReview.url" :src="preprocessReview.url" alt="" style="width: 100%; height: 72px; object-fit: contain; background: var(--v-bg); border: 1px solid var(--v-accent); border-radius: var(--r2);" />
      </div>
      <div class="v-card-title" style="font-size: var(--fs-small);">{{ preprocessReview.scene }} · {{ preprocessReview.confidence }}</div>
      <div class="v-card-meta" style="margin-top: var(--s2);">{{ preprocessReview.elapsed }} · {{ preprocessReview.strategy }}</div>
      <button v-if="preprocessReview.url" class="v-state-tab" type="button" style="margin-top: var(--s3); width: 100%;" @click="showPreprocessModal = true">{{ t('audit_view_compare') }}</button>
    </div>

    <div class="v-confidence-panel">
      <div class="v-confidence-row">
        <span>{{ t('audit_ocr_conf') }}</span>
        <span :class="confidenceClass">{{ confidenceText }}</span>
      </div>
      <div class="v-confidence-row">
        <span>{{ t('audit_scene') }}</span>
        <span class="v-confidence-value">{{ sceneText }}</span>
      </div>
      <div class="v-confidence-row">
        <span>{{ t('audit_diff') }}</span>
        <span class="v-confidence-error">{{ diffCount }}</span>
      </div>
    </div>

    <div v-if="hasError" class="v-review-section" style="margin-top: var(--s3); border-color: var(--v-error);">
      <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: var(--s2);">Error</div>
      <div class="v-small" style="color: var(--v-error);">{{ currentError.message }}</div>
    </div>

    <div class="v-review-section" style="margin-top: var(--s3);">
      <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: var(--s2);">{{ t('audit_local_api') }}</div>
      <div class="v-api-url">127.0.0.1 : sidecar</div>
      <div class="v-api-desc">{{ t('audit_local_api_desc') }}</div>
    </div>

    <div class="v-review-section" style="margin-top: var(--s3);">
      <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: var(--s2);">{{ t('audit_actions') }}</div>
      <div class="v-small" style="margin-bottom: var(--s3);">{{ t('audit_export_hint') }}</div>
      <div class="v-state-tabs export-mode-tabs" style="height: auto; flex-wrap: wrap; margin-bottom: var(--s3);">
        <button
          v-for="item in exportTabs"
          :key="item.key"
          type="button"
          class="v-state-tab"
          :class="{ 'is-active': exportMode === item.key }"
          :disabled="!hasResult"
          @click="exportMode = item.key"
        >
          {{ t(item.labelKey) }}
        </button>
      </div>
      <div class="export-format-row">
        <button v-if="exportMode === 'copy'" class="v-export-btn" type="button" :disabled="!hasResult" @click="copyCurrent">{{ t('audit_action_copy') }}</button>
        <template v-else>
          <button class="v-export-btn" type="button" :disabled="!hasResult" @click="downloadCurrent('txt')">{{ t('audit_export_txt') }}</button>
          <button class="v-export-btn" type="button" :disabled="!hasResult" @click="downloadCurrent('md')">{{ t('audit_export_md') }}</button>
          <button class="v-export-btn" type="button" :disabled="!hasResult" @click="downloadCurrent('docx')">{{ t('audit_export_docx') }}</button>
        </template>
      </div>
      <div class="v-state-tabs audit-command-row" style="height: auto; flex-wrap: wrap; margin-top: var(--s3);">
        <button
          class="v-state-tab"
          type="button"
          :class="{ 'is-active': aiStream.status.value === 'streaming' }"
          :disabled="!hasResult || aiStream.status.value === 'streaming'"
          @click="reRefine"
        >
          {{ aiStream.status.value === 'streaming' ? t('audit_refining') : t('audit_re_refine') }}
        </button>
        <button class="v-state-tab" type="button" :disabled="!preprocessReview" @click="showPreprocessModal = true">{{ t('audit_reprocess') }}</button>
        <button class="v-state-tab" type="button" :disabled="!preprocessReview?.originalUrl" @click="showPreprocessModal = true">{{ t('audit_view_original') }}</button>
      </div>
    </div>

    <div v-if="showPreprocessModal && preprocessReview" style="position: fixed; inset: 0; z-index: 50; display: grid; place-items: center; background: color-mix(in srgb, var(--v-bg) 86%, transparent);" @click="showPreprocessModal = false">
      <div class="v-panel-rail" style="position: relative; width: min(1100px, calc(100vw - var(--s12))); max-height: calc(100vh - var(--s12)); padding: var(--s5);" @click.stop>
        <button class="v-state-tab" type="button" style="position: absolute; top: var(--s3); right: var(--s3); width: 32px; padding: 0;" @click="showPreprocessModal = false">×</button>
        <div class="v-caption" style="text-transform: uppercase; letter-spacing: 0.08em;">Preprocess Compare</div>
        <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s4); margin-top: var(--s4);">
          <img v-if="preprocessReview.originalUrl" :src="preprocessReview.originalUrl" alt="" style="width: 100%; max-height: calc(100vh - 180px); object-fit: contain; background: var(--v-bg); border: 1px dashed var(--v-border); border-radius: var(--r3);" />
          <img v-if="preprocessReview.url" :src="preprocessReview.url" alt="" style="width: 100%; max-height: calc(100vh - 180px); object-fit: contain; background: var(--v-bg); border: 1px solid var(--v-accent); border-radius: var(--r3);" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { exportSingle, copyResult } from '../utils/exporters'
import { showToast } from '../composables/useToast'
import { t } from '../i18n'
import { useAIStream } from '../composables/useAIStream'

const taskStore = useTaskStore()
const aiStream = useAIStream()
const showPreprocessModal = ref(false)
const exportMode = ref('polished')

const exportTabs = [
  { key: 'raw', labelKey: 'audit_action_raw' },
  { key: 'polished', labelKey: 'audit_action_refined' },
  { key: 'compare', labelKey: 'audit_action_dual' },
  { key: 'copy', labelKey: 'audit_action_copy' },
]

const currentResult = computed(() => {
  const id = taskStore.currentTask?.id
  return id ? taskStore.getResult(id) : null
})

const currentError = computed(() => {
  const id = taskStore.currentTask?.id
  return id ? taskStore.getError(id) : null
})

const hasResult = computed(() => !!currentResult.value)
const hasError = computed(() => !!currentError.value)

const reviewStatus = computed(() => {
  if (hasError.value) return t('audit_status_error')
  if (taskStore.isProcessing || taskStore.currentTask?.status === 'processing') return t('audit_status_running')
  if (hasResult.value) return t('audit_status_ready')
  return t('audit_status_waiting')
})

const currentTaskMeta = computed(() => {
  const task = taskStore.currentTask
  if (!task) return 'NO FILE SELECTED'
  const size = task.size ? `${(task.size / 1024).toFixed(1)}KB` : 'HISTORY'
  return `${String(task.status || 'pending').toUpperCase()} · ${size}`
})

const confidenceText = computed(() => {
  const value = currentResult.value?.confidence
  if (value === undefined || value === null) return '--'
  return `${(Number(value) * 100).toFixed(1)}%`
})

const confidenceClass = computed(() => {
  const value = Number(currentResult.value?.confidence || 0)
  return value > 0 && value < 0.85 ? 'v-confidence-error' : 'v-confidence-value'
})

const sceneText = computed(() => currentResult.value?.scene || '--')
const diffCount = computed(() => currentResult.value?.ai?.diff?.length || 0)

const preprocessReview = computed(() => {
  const task = taskStore.currentTask
  const result = currentResult.value
  const resultPrep = result?.preprocess || null
  const storePrep = task ? taskStore.getPreprocessJob(task.id) : null
  const prep = resultPrep || storePrep
  if (!prep && !result?.preprocess_steps?.length) return null
  return {
    scene: prep?.frontend_scene || prep?.scene || result?.scene || '--',
    confidence: prep?.scene_confidence ? `${Math.round(prep.scene_confidence * 100)}%` : '--',
    elapsed: `${prep?.elapsed_ms || prep?.time_ms || result?.preprocess_time_ms || 0}ms`,
    strategy: prep?.strategy || 'history',
    url: storePrep?.processed_full_url || prep?.processed_full_url || '',
    originalUrl: storePrep?.original_full_url || prep?.original_full_url || '',
  }
})

async function copyCurrent() {
  if (!currentResult.value) return
  try {
    await copyResult(currentResult.value, 'polished')
    showToast({ type: 'success', message: t('toast_copied'), duration: 2000 })
  } catch (error) {
    showToast({ type: 'error', message: t('toast_copy_failed'), duration: 3000 })
  }
}

async function downloadCurrent(format) {
  if (!currentResult.value) return
  await exportSingle(currentResult.value, taskStore.currentTask?.name || 'ocr-result', exportMode.value, format)
}

async function reRefine() {
  const result = currentResult.value
  const taskId = taskStore.currentTask?.id
  if (!result || !taskId || !result.text) return
  try {
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
      showToast({ type: 'success', message: t('toast_refine_done'), duration: 1800 })
    }
  } catch (error) {
    showToast({ type: 'error', message: `${t('toast_refine_failed')}: ${error?.message || error}`, duration: 3600 })
  }
}
</script>

<style scoped>
.export-mode-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--s2);
}

.export-mode-tabs .v-state-tab {
  width: 100%;
  min-width: 0;
  padding-inline: var(--s2);
}

.export-format-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--s2);
}

.export-format-row .v-export-btn {
  width: 100%;
  height: 40px;
  min-height: 40px;
  font-size: var(--fs-small);
}

.export-format-row .v-export-btn:only-child {
  grid-column: 1 / -1;
}

.audit-command-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--s2);
}

.audit-command-row .v-state-tab {
  width: 100%;
  min-width: 0;
  padding-inline: var(--s2);
  white-space: normal;
}
</style>
