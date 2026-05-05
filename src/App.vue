<template>
  <BackendConsole v-if="showBackendConsole" @close="showBackendConsole = false" />
  <div v-else class="v-app-shell">

    <header class="v-topbar">
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
        <button class="icon-btn" type="button" title="打开项目文档" @click="openDocs">
          <span class="docs-icon" aria-hidden="true"></span>
          <span>文档</span>
        </button>
        <button class="icon-btn" type="button" title="配置" @click="showConfig = true">
          <span class="gear-icon" aria-hidden="true"></span>
          <span>配置</span>
        </button>
      </div>
    </header>

    <aside class="v-left-rail">
      <UploadZone variant="queue" />
    </aside>

    <main class="v-workbench">
      <UploadZone v-if="!hasResult && !hasError" variant="dropzone" />
      <ResultPanel v-else />
    </main>

    <aside class="v-review-lamp">
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
    </aside>

    <footer class="v-bottombar">
      <span class="v-readout-accent">LOCAL HELD</span>
      <span class="v-readout-strong">MODEL {{ modelLabel }}</span>
      <span class="v-readout">QUEUE {{ queueText }}</span>
      <span class="v-readout">{{ reviewStatus }}</span>
    </footer>

    <ConfigDrawer v-model:visible="showConfig" @open-ai-center="showAIProviderCenter = true" />
    <AIProviderModal v-model:visible="showAIProviderCenter" />
    <ToastStack />
    <DialogSystem />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useTaskStore } from './stores/taskStore'
import { useConfigStore } from './stores/configStore'
import { useThemeStore } from './stores/themeStore'
import UploadZone from './components/UploadZone.vue'
import ResultPanel from './components/ResultPanel.vue'
import BackendConsole from './components/BackendConsole.vue'
import ConfigDrawer from './components/ConfigDrawer.vue'
import AIProviderModal from './components/AIProviderModal.vue'
import ToastStack from './components/ToastStack.vue'
import DialogSystem from './components/DialogSystem.vue'

import { openDocs } from './api/tauri_ipc'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const themeStore = useThemeStore()
const showConfig = ref(false)
const showAIProviderCenter = ref(false)
const showBackendConsole = ref(false)

const themeButtonLabel = computed(() => {
  const theme = themeStore.resolvedTheme
  return theme === 'light' ? '白' : '黑'
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
  themeStore.setTheme(themeStore.resolvedTheme === 'light' ? 'dark' : 'light')
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
.v-app-shell {
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr) var(--bottombar-h);
  grid-template-columns: var(--left-rail-w) minmax(0, 1fr) var(--right-review-w);
  gap: var(--layout-gap);
  padding: var(--layout-pad);
  height: 100vh;
  background: var(--v-bg);
  overflow: hidden;
}

.v-topbar,
.v-bottombar,
.v-left-rail,
.v-workbench,
.v-review-lamp {
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
}

.v-topbar {
  grid-column: 1 / -1;
  height: var(--topbar-h);
  background: var(--v-rail);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-inline: var(--s4);
  min-width: 0;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: var(--s3);
  min-width: 0;
}

.brand-mark {
  width: 18px;
  height: 18px;
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
  font-size: var(--fs-h2);
  line-height: 1;
}

.brand-sub {
  margin-top: 3px;
}

.top-readouts {
  display: flex;
  align-items: center;
  gap: var(--s5);
  min-width: 0;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: var(--s2);
  flex-shrink: 0;
}

.icon-btn {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: var(--s2);
  padding-inline: var(--s3);
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  cursor: pointer;
}

.icon-btn:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.gear-icon {
  width: 13px;
  height: 13px;
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
  width: 14px;
  height: 14px;
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
  width: 15px;
  height: 12px;
  border: 1px solid currentColor;
  border-radius: var(--r1);
  position: relative;
}

.console-icon::before {
  content: "";
  position: absolute;
  left: 3px;
  top: 3px;
  width: 4px;
  height: 4px;
  border-right: 1px solid currentColor;
  border-bottom: 1px solid currentColor;
  transform: rotate(-45deg);
}

.console-icon::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 4px;
  height: 1px;
  background: currentColor;
}

.docs-icon {
  width: 13px;
  height: 15px;
  border: 1px solid currentColor;
  border-radius: var(--r1);
  position: relative;
}

.docs-icon::before,
.docs-icon::after {
  content: "";
  position: absolute;
  left: 3px;
  right: 3px;
  height: 1px;
  background: currentColor;
}

.docs-icon::before {
  top: 5px;
}

.docs-icon::after {
  top: 9px;
}

.v-left-rail {
  grid-row: 2;
  grid-column: 1;
  min-width: 0;
  overflow: auto;
  background: var(--v-rail);
  padding: var(--s4);
}

.v-workbench {
  grid-row: 2;
  grid-column: 2;
  min-width: 0;
  overflow: auto;
  background: var(--v-panel);
  padding: var(--s5);
}

.v-review-lamp {
  grid-row: 2;
  grid-column: 3;
  min-width: 0;
  overflow: auto;
  background: var(--v-rail);
  padding: var(--s4);
}

.v-bottombar {
  grid-column: 1 / -1;
  height: var(--bottombar-h);
  background: var(--v-rail);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s4);
  padding-inline: var(--s4);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  min-width: 0;
}

.v-review-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--s4);
}

.v-review-status,
.section-label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-muted);
  letter-spacing: 0.08em;
}

.review-title {
  margin-top: var(--s1);
  font-size: var(--fs-h2);
}

.lamp-dot {
  width: 10px;
  height: 10px;
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

.case-name {
  margin-top: var(--s2);
  color: var(--v-text);
  font-size: var(--fs-small);
  line-height: 1.45;
  word-break: break-word;
}

.case-meta {
  margin-top: var(--s2);
}

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
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.v-confidence-row + .v-confidence-row {
  margin-top: var(--s3);
}

.v-confidence-value {
  color: var(--v-accent);
}

.v-confidence-error,
.error-text {
  color: var(--v-error);
}

.v-api-url {
  margin-top: var(--s2);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-accent);
}

.v-api-desc {
  margin-top: var(--s1);
  font-size: var(--fs-micro);
  color: var(--v-text-muted);
}

@media (max-width: 1023px) and (min-width: 768px) {
  .top-readouts {
    gap: var(--s3);
  }

  .icon-btn span:last-child {
    display: none;
  }
}

@media (max-width: 767px) {
  .v-app-shell {
    grid-template-rows: 48px 132px minmax(0, 1fr) auto 40px;
    grid-template-columns: 1fr;
    gap: var(--s4);
    padding: var(--s4);
  }

  .v-topbar {
    grid-row: 1;
    grid-column: 1;
  }

  .top-readouts {
    display: none;
  }

  .top-actions {
    gap: var(--s1);
  }

  .icon-btn {
    padding-inline: var(--s2);
  }

  .icon-btn span:last-child {
    display: none;
  }

  .v-left-rail {
    grid-row: 2;
    grid-column: 1;
    height: 132px;
    overflow: auto;
  }

  .v-workbench {
    grid-row: 3;
    grid-column: 1;
  }

  .v-review-lamp {
    grid-row: 4;
    grid-column: 1;
    max-height: 280px;
  }

  .v-bottombar {
    grid-row: 5;
    grid-column: 1;
    overflow: hidden;
  }
}
</style>
