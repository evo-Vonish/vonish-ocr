<template>
  <BackendConsole v-if="showBackendConsole" @close="showBackendConsole = false" />
  <DocsViewer v-else-if="showDocs" @close="showDocs = false" />
  <ResponsiveShell v-else>
    <template #topbar>
      <div class="brand-block">
        <span class="brand-mark" aria-hidden="true"></span>
        <div>
          <div class="brand-title v-title">VonishOCR</div>
          <div class="brand-sub v-micro">LOCAL EVIDENCE DESK</div>
        </div>
      </div>
      <div class="top-readouts">
        <span class="v-readout-accent">LOCAL HELD</span>
        <span class="v-readout">MODEL {{ modelLabel }}</span>
        <span class="v-readout">QUEUE {{ queueText }}</span>
      </div>
      <div class="top-actions">
        <button class="icon-btn" type="button" :title="`显示模式：${themeButtonLabel}`" @click="cycleTheme">
          <span class="theme-icon" aria-hidden="true"></span>
          <span>{{ themeButtonLabel }}</span>
        </button>
        <button class="icon-btn" type="button" title="后端控制台" @click="showBackendConsole = true">
          <span class="console-icon" aria-hidden="true"></span>
          <span>后端控制台</span>
        </button>
        <button class="icon-btn" type="button" title="打开项目文档" @click="showDocs = true">
          <span class="docs-icon" aria-hidden="true"></span>
          <span>文档</span>
        </button>
        <button class="icon-btn" type="button" title="配置" @click="showConfig = true">
          <span class="gear-icon" aria-hidden="true"></span>
          <span>配置</span>
        </button>
      </div>
    </template>

    <template #left-rail>
      <EvidenceQueue />
    </template>

    <template #workbench>
      <UploadZone v-if="!hasResult && !hasError" variant="dropzone" />
      <ResultPanel v-else />
    </template>

    <template #right-review>
      <div class="v-review-head">
        <div>
          <div class="v-review-status">{{ reviewStatus }}</div>
          <div class="review-title v-title">复核灯</div>
        </div>
        <span class="lamp-dot" :class="{ on: hasResult || hasError }"></span>
      </div>
      <div class="v-review-section">
        <div class="section-label">CURRENT CASE</div>
        <div class="case-name">{{ taskStore.currentTask?.name || '等待证据文件' }}</div>
        <div class="case-meta v-mono">{{ currentTaskMeta }}</div>
      </div>
      <div v-if="preprocessReview" class="v-review-section">
        <div class="section-label">PREPROCESS</div>
        <div v-if="preprocessReview.url || preprocessReview.originalUrl" class="review-prep-strip">
          <img v-if="preprocessReview.originalUrl" :src="preprocessReview.originalUrl" alt="" />
          <img v-if="preprocessReview.url" :src="preprocessReview.url" alt="" />
        </div>
        <div class="case-name">{{ preprocessReview.scene }} · {{ preprocessReview.confidence }}</div>
        <div class="case-meta v-mono">{{ preprocessReview.elapsed }} · {{ preprocessReview.strategy }}</div>
        <button v-if="preprocessReview.url" class="text-link" type="button" @click="showPreprocessModal = true">查看对比图</button>
      </div>
      <div class="v-confidence-panel">
        <div class="v-confidence-row">
          <span>OCR CONF</span>
          <span :class="confidenceClass">{{ confidenceText }}</span>
        </div>
        <div class="v-confidence-row">
          <span>SCENE</span>
          <span>{{ sceneText }}</span>
        </div>
        <div class="v-confidence-row">
          <span>DIFF</span>
          <span>{{ diffCount }}</span>
        </div>
      </div>
      <div v-if="hasError" class="v-review-section error-block">
        <div class="section-label">ERROR</div>
        <div class="error-text">{{ currentError.message }}</div>
      </div>
      <div class="v-review-section">
        <div class="section-label">LOCAL API</div>
        <div class="v-api-url">127.0.0.1 : sidecar</div>
        <div class="v-api-desc">本地推理优先，AI 修复可选。</div>
      </div>
    </template>

    <template #bottombar>
      <span class="v-readout-accent">LOCAL HELD</span>
      <span class="v-readout-strong">MODEL {{ modelLabel }}</span>
      <span class="v-readout">QUEUE {{ queueText }}</span>
      <span class="v-readout">{{ reviewStatus }}</span>
    </template>

    <template #top-toolbar>
      <div class="mobile-toolbar">
        <div class="toolbar-scroll">
          <div v-if="taskStore.tasks.length" class="toolbar-section">
            <span class="toolbar-label">队列</span>
            <div class="toolbar-chips">
              <div v-for="t in taskStore.tasks.slice(0, 10)" :key="t.id" class="toolbar-chip" :class="{ active: t.id === taskStore.currentTask?.id }" @click="taskStore.currentTaskId = t.id">
                {{ t.name?.slice(0, 8) || t.id }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </ResponsiveShell>

  <ConfigDrawer v-model:visible="showConfig" @open-ai-center="showAIProviderCenter = true" />
  <div v-if="showPreprocessModal && preprocessReview" class="modal-backdrop" @click="showPreprocessModal = false">
    <div class="preprocess-modal" @click.stop>
      <button class="modal-close" type="button" @click="showPreprocessModal = false">×</button>
      <div class="section-label">PREPROCESS COMPARE</div>
      <div class="modal-images">
        <img v-if="preprocessReview.originalUrl" :src="preprocessReview.originalUrl" alt="" />
        <img v-if="preprocessReview.url" :src="preprocessReview.url" alt="" />
      </div>
    </div>
  </div>
  <AIProviderModal v-model:visible="showAIProviderCenter" />
  <ToastStack />
  <DialogSystem />
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useTaskStore } from './stores/taskStore'
import { useConfigStore } from './stores/configStore'
import { useThemeStore } from './stores/themeStore'
import UploadZone from './components/UploadZone.vue'
import EvidenceQueue from './components/EvidenceQueue.vue'
import ResultPanel from './components/ResultPanel.vue'
import BackendConsole from './components/BackendConsole.vue'
import DocsViewer from './components/DocsViewer.vue'
import ConfigDrawer from './components/ConfigDrawer.vue'
import AIProviderModal from './components/AIProviderModal.vue'
import ToastStack from './components/ToastStack.vue'
import DialogSystem from './components/DialogSystem.vue'
import ResponsiveShell from './layouts/ResponsiveShell.vue'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const themeStore = useThemeStore()
const showConfig = ref(false)
const showAIProviderCenter = ref(false)
const showBackendConsole = ref(false)
const showDocs = ref(false)
const showPreprocessModal = ref(false)

const themeButtonLabel = computed(() => {
  return themeStore.resolvedMode === 'light' ? '白' : '黑'
})

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

const modelLabel = computed(() => {
  const id = configStore.config.ocr_model || 'rapidocr-mobile-cn'
  if (id.includes('rapidocr')) return '极速'
  if (id.includes('cnocr')) return '均衡'
  if (id.includes('paddle')) return '精度'
  return id
})

const queueText = computed(() => {
  const total = taskStore.tasks.length.toString().padStart(2, '0')
  const active = taskStore.processingCount + taskStore.pendingCount
  return `${active.toString().padStart(2, '0')} / ${total}`
})

const reviewStatus = computed(() => {
  if (hasError.value) return 'AUDIT ERROR'
  if (taskStore.isProcessing || taskStore.currentTask?.status === 'processing') return 'OCR RUNNING'
  if (hasResult.value) return 'AUDIT READY'
  return 'AUDIT WAITING'
})

const currentTaskMeta = computed(() => {
  const task = taskStore.currentTask
  if (!task) return 'NO FILE SELECTED'
  const size = task.size ? `${(task.size / 1024).toFixed(1)}KB` : 'HISTORY'
  return `${task.status.toUpperCase()} · ${size}`
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

function cycleTheme() {
  themeStore.setThemeMode(themeStore.resolvedMode === 'light' ? 'dark' : 'light')
}

onMounted(() => {
  themeStore.loadTheme()
  themeStore.watchSystemTheme()
  taskStore.restorePersisted()
  configStore.loadConfig()
  configStore.loadModels()
  const splash = document.getElementById('splash')
  if (splash) {
    splash.classList.add('hidden')
    setTimeout(() => { splash.style.display = 'none' }, 400)
  }
})
</script>

<style scoped>
.brand-block {
  display: flex;
  align-items: center;
  gap: var(--s3);
  min-width: 0;
  flex-shrink: 0;
}

.brand-mark {
  width: clamp(14px, 1.2vw, 18px);
  height: clamp(14px, 1.2vw, 18px);
  border: 1px solid var(--v-accent);
  border-radius: var(--r2);
  position: relative;
  box-shadow: var(--glow-soft);
}

.brand-mark::after {
  content: "";
  position: absolute;
  inset: 5px;
  background: var(--v-accent);
  border-radius: var(--r1);
}

.brand-title {
  font-size: var(--font-h2);
  line-height: 1;
}

.brand-sub {
  margin-top: 3px;
}

.top-readouts {
  display: flex;
  align-items: center;
  gap: clamp(8px, 2vw, var(--s5));
  min-width: 0;
  transition: opacity 0.15s ease, gap 0.2s ease;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: clamp(3px, 0.8vw, var(--s2));
  flex-shrink: 0;
  flex-wrap: nowrap;
  transition: gap 0.2s ease;
}

.icon-btn {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: clamp(4px, 0.8vw, var(--s2));
  padding-inline: var(--s3);
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  cursor: pointer;
  font-family: var(--font-body);
  white-space: nowrap;
  flex-shrink: 0;
  transition: padding-inline 0.2s ease, height 0.2s ease, gap 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, color 0.2s ease;
}

.icon-btn span:last-child {
  transition: opacity 0.15s ease, max-width 0.15s ease;
}

.icon-btn:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.gear-icon {
  width: 13px; height: 13px;
  border: 1px solid currentColor;
  border-radius: 50%;
  position: relative;
}

.gear-icon::after {
  content: "";
  position: absolute;
  inset: 4px;
  background: currentColor;
  border-radius: 50%;
}

.theme-icon {
  width: 14px; height: 14px;
  border: 1px solid currentColor;
  border-radius: 50%;
  position: relative;
  overflow: hidden;
}

.theme-icon::before {
  content: "";
  position: absolute;
  inset: 0 50% 0 0;
  background: currentColor;
}

.console-icon {
  width: 15px; height: 12px;
  border: 1px solid currentColor;
  border-radius: var(--r1);
  position: relative;
}

.console-icon::before {
  content: "";
  position: absolute;
  left: 3px; top: 3px;
  width: 4px; height: 4px;
  border-right: 1px solid currentColor;
  border-bottom: 1px solid currentColor;
  transform: rotate(-45deg);
}

.console-icon::after {
  content: "";
  position: absolute;
  right: 3px; bottom: 3px;
  width: 4px; height: 1px;
  background: currentColor;
}

.docs-icon {
  width: 13px; height: 15px;
  border: 1px solid currentColor;
  border-radius: var(--r1);
  position: relative;
}

.docs-icon::before,
.docs-icon::after {
  content: "";
  position: absolute;
  left: 3px; right: 3px;
  height: 1px;
  background: currentColor;
}

.docs-icon::before { top: 5px; }
.docs-icon::after { top: 9px; }

/* ── 复核灯内容 ── */
.v-review-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--s4);
}

.v-review-status,
.section-label {
  font-family: var(--font-mono);
  font-size: var(--font-micro);
  color: var(--v-text-muted);
  letter-spacing: 0.08em;
}

.review-title {
  margin-top: var(--s1);
  font-size: var(--font-h2);
}

.lamp-dot {
  width: clamp(8px, 0.8vw, 10px);
  height: clamp(8px, 0.8vw, 10px);
  border: 1px solid var(--v-border-strong);
  border-radius: 50%;
}

.lamp-dot.on {
  background: var(--v-accent);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.v-review-section {
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s3);
}

.v-review-section + .v-review-section,
.v-confidence-panel + .v-review-section,
.v-review-section + .v-confidence-panel {
  margin-top: var(--s3);
}

.text-link {
  margin-top: var(--s2);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--v-accent);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  cursor: pointer;
}

.review-prep-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s2);
  margin-top: var(--s3);
}

.review-prep-strip img {
  width: 100%;
  height: 84px;
  object-fit: contain;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.72);
}

.preprocess-modal {
  width: min(1100px, calc(100vw - 64px));
  max-height: calc(100vh - 64px);
  position: relative;
  padding: var(--s5);
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
}

.modal-close {
  position: absolute;
  top: var(--s3);
  right: var(--s3);
  width: 28px;
  height: 28px;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  background: transparent;
  color: var(--v-text);
  cursor: pointer;
}

.modal-images {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s4);
  margin-top: var(--s4);
}

.modal-images img {
  width: 100%;
  max-height: calc(100vh - 180px);
  object-fit: contain;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.case-name {
  margin-top: var(--s2);
  color: var(--v-text);
  font-size: var(--font-small);
  line-height: 1.45;
  word-break: break-word;
}

.case-meta { margin-top: var(--s2); }

.v-confidence-panel {
  padding: var(--s4);
  background: var(--v-panel-raised);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.v-confidence-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  font-family: var(--font-mono);
  font-size: var(--font-caption);
  color: var(--v-text-muted);
}

.v-confidence-row + .v-confidence-row { margin-top: var(--s3); }

.v-confidence-value { color: var(--v-accent); }

.v-confidence-error,
.error-text { color: var(--v-error); }

.v-api-url {
  margin-top: var(--s2);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-accent);
}

.v-api-desc {
  margin-top: var(--s1);
  font-size: var(--font-micro);
  color: var(--v-text-muted);
}

/* ── 移动端顶部工具栏 ── */
.mobile-toolbar {
  padding: var(--space-sm) var(--space-md);
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.toolbar-scroll {
  overflow-x: auto;
  display: flex;
  gap: var(--space-md);
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.toolbar-label {
  font-family: var(--font-mono);
  font-size: var(--font-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.toolbar-chips {
  display: flex;
  gap: var(--space-xs);
}

.toolbar-chip {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  font-size: var(--font-caption);
  color: var(--v-text-muted);
  white-space: nowrap;
  cursor: pointer;
}

.toolbar-chip.active {
  border-color: var(--v-accent);
  color: var(--v-accent);
}

/* ── 响应式 ── */
@media (max-width: 1023px) and (min-width: 768px) {
  .top-readouts { gap: clamp(6px, 1vw, var(--s3)); }
  .icon-btn span:last-child { opacity: 0; max-width: 0; overflow: hidden; }
  .icon-btn { padding-inline: var(--s2); gap: 0; }
  .brand-sub { display: none; }
}

@media (max-width: 767px) {
  .top-readouts { display: none; }
  .top-actions { gap: 3px; }
  .icon-btn { padding-inline: 6px; height: 28px; gap: 0; }
  .icon-btn span:last-child { opacity: 0; max-width: 0; overflow: hidden; }
  .brand-sub { display: none; }
  .brand-title { font-size: var(--font-small); }
}
</style>
