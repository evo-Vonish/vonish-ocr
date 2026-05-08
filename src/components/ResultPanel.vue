<template>
  <section class="result-panel">
    <div class="result-head">
      <div>
        <div class="result-kicker">OCR RESULT</div>
        <h2 class="result-title v-title">{{ currentName }}</h2>
      </div>
      <div class="state-tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          type="button"
          class="state-tab"
          :class="{ active: activeTab === t.key }"
          @click="activeTab = t.key"
        >
          {{ t.label }}
        </button>
      </div>
    </div>

    <div v-if="displayError" class="error-card">
      <div class="error-label">OCR ERROR</div>
      <div class="error-title">识别失败</div>
      <div class="error-message">{{ displayError.message }}</div>
      <div class="error-hint">{{ errorHint(displayError.code) }}</div>
      <div class="error-actions">
        <button class="text-btn" type="button" @click="showErrorDetail = !showErrorDetail">
          {{ showErrorDetail ? '收起' : '详情' }}
        </button>
        <button class="text-btn" type="button" @click="copyError">复制</button>
        <button class="text-btn" type="button" @click="reportError">汇报</button>
      </div>
      <pre v-if="showErrorDetail" class="error-json">{{ errorDetailJson }}</pre>
    </div>

    <div v-else-if="isLoading" class="loading-card">
      <div class="paper-stage">
        <span class="doc-line wide"></span>
        <span class="doc-line"></span>
        <span class="doc-line short"></span>
        <span class="v-scan-line"></span>
      </div>
      <div class="loading-text v-mono-accent">LOCAL OCR RUNNING</div>
    </div>

    <div v-else-if="!rawResult" class="empty-state">
      <div class="empty-title v-display">等待识别结果</div>
      <div class="empty-text">左侧选择证据文件后开始本地 OCR，结果会进入此工作台。</div>
    </div>

    <div v-else class="result-body">
      <div v-if="activeTab === 'raw'" class="single-result paper-col">
        <div class="tab-title-row">
          <div class="result-label">RAW OCR</div>
          <span class="result-chip">{{ formatConfidence(displayResult.confidence) }}</span>
        </div>
        <MdRender class="evidence-text" :text="displayResult.text || '暂无识别结果'" />
      </div>

      <div v-if="activeTab === 'polished'" class="single-result">
        <div class="stream-head">
          <div>
            <div class="result-label">AI POLISHED</div>
            <div v-if="displayResult.aiError" class="quiet-note is-error">自动修复出错：{{ displayResult.aiError.message }}</div>
          </div>
          <div class="stream-actions">
            <span v-if="streamStatus === 'streaming'" class="stream-pulse">AI 正在复核...</span>
            <button v-if="streamStatus === 'streaming'" class="text-btn" type="button" @click="stopRefine">停止</button>
            <button v-else class="text-btn" type="button" :disabled="!displayResult.text" @click="startRefine">重新精修</button>
          </div>
        </div>
        <MdRender class="evidence-text" :text="streamedText || displayResult.polished || '暂无精修结果'" />
        <div v-if="streamStatus === 'error'" class="quiet-note is-error">AI 修复失败：{{ aiStream.error.value?.message || '未知错误' }}</div>
        <div v-if="streamStatus === 'interrupted'" class="quiet-note">精修已中断，已保留当前输出。</div>
      </div>

      <div v-if="activeTab === 'diff'" class="single-result">
        <div class="tab-title-row">
          <div class="result-label">DIFF RECORD</div>
          <span class="result-chip">{{ displayResult.diff.length }}</span>
        </div>
        <div v-if="!displayResult.diff.length" class="quiet-note">无修改记录。</div>
        <div v-else class="diff-list">
          <div v-for="(d, i) in displayResult.diff" :key="i" class="diff-line">
            <span class="diff-from v-delete-mark">{{ d.original || '-' }}</span>
            <span class="diff-arrow">-&gt;</span>
            <span class="diff-to v-insert-mark">{{ d.fixed || '-' }}</span>
            <span v-if="d.reason" class="diff-reason">{{ d.reason }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="export-panel" :class="{ disabled: !hasResult }" :title="hasResult ? '' : '请先完成识别'">
      <div class="export-tabs">
        <button
          v-for="tab in exportTabs"
          :key="tab.key"
          type="button"
          class="export-tab"
          :class="{ active: exportMode === tab.key }"
          :disabled="!hasResult"
          @click="exportMode = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="export-actions">
        <button v-if="exportMode === 'copy'" class="export-btn" type="button" :disabled="!hasResult" @click="copyCurrent">复制</button>
        <template v-else>
          <button class="export-btn" type="button" :disabled="!hasResult" @click="downloadCurrent('txt')">TXT</button>
          <button class="export-btn" type="button" :disabled="!hasResult" @click="downloadCurrent('md')">MD</button>
          <button class="export-btn" type="button" :disabled="!hasResult" @click="downloadCurrent('docx')">DOCX</button>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import MdRender from './MdRender.vue'
import { useTaskStore } from '../stores/taskStore'
import { useAIStream } from '../composables/useAIStream'
import { copyResult, exportSingle } from '../utils/exporters'
import { showToast } from '../composables/useToast'

const taskStore = useTaskStore()
const aiStream = useAIStream()

const tabs = [
  { key: 'raw', label: '原始' },
  { key: 'polished', label: '精修' },
  { key: 'diff', label: 'Diff' },
]
const exportTabs = [
  { key: 'raw', label: '原文本' },
  { key: 'polished', label: '修复后' },
  { key: 'compare', label: '双结果对比' },
  { key: 'copy', label: '复制' },
]

const activeTab = ref('raw')
const exportMode = ref('polished')
const showPreprocessDetail = ref(false)
const showErrorDetail = ref(false)

const SCENE_NAMES = {
  printed_document: '打印文档',
  handwritten_note: '手写笔记',
  screenshot: '截屏',
  id_card: '身份证',
  table_form: '表格',
  photo_with_text: '户外照片',
  low_quality_scan: '低质量扫描',
  exam_paper: '试卷',
}

const currentName = computed(() => taskStore.currentTask?.name || '未选择文件')
const rawResult = computed(() => taskStore.currentTask ? taskStore.getResult(taskStore.currentTask.id) : null)
const hasResult = computed(() => !!rawResult.value?.text)
const streamStatus = computed(() => aiStream.status.value)
const streamedText = computed(() => aiStream.text.value)

const isLoading = computed(() => {
  const current = taskStore.currentTask
  return !!current && current.status === 'processing' && !rawResult.value
})

const displayError = computed(() => taskStore.currentTask ? taskStore.getError(taskStore.currentTask.id) : null)

const preprocessInfo = computed(() => {
  const result = rawResult.value
  if (!result) return null
  const prep = result.preprocess || {}
  const storeJob = taskStore.currentTask ? taskStore.getPreprocessJob(taskStore.currentTask.id) : null
  return {
    scene: prep.frontend_scene || prep.scene || result.scene || '',
    steps: prep.steps || result.preprocess_steps || [],
    timeMs: prep.time_ms || result.preprocess_time_ms || 0,
    usedOriginal: prep.used_original || result.preprocess_used_original || false,
    confidence: prep.scene_confidence || 0,
    quality: prep.quality_score || 0,
    processedUrl: storeJob?.processed_full_url || prep.processed_full_url || '',
  }
})

const displayResult = computed(() => {
  const result = rawResult.value
  const ai = result?.ai || {}
  return {
    text: result?.text || '',
    confidence: result?.confidence || 0,
    polished: ai.polished || result?.text || '',
    aiConfidence: ai.confidence || result?.confidence || 0,
    diff: ai.diff || [],
    uncertain: ai.uncertain || [],
    failoverNotice: ai.failover_notice || '',
    aiError: ai.error || null,
  }
})

function formatPreprocessSummary(info) {
  if (!info?.scene) return ''
  const sceneName = SCENE_NAMES[info.scene] || info.scene
  if (info.scene === 'screenshot') return `${sceneName} · 已跳过预处理`
  if (info.usedOriginal) return `${sceneName} · 已回退原图`
  return `${sceneName} · ${info.timeMs || 0}ms`
}

function errorHint(code) {
  const hints = {
    MODEL_NOT_LOADED: '请先下载并加载 OCR 模型。',
    MODEL_LOAD_ERROR: '模型文件可能损坏，请重新下载。',
    OCR_ENGINE_ERROR: '图片格式可能不支持，请尝试 JPG 或 PNG。',
    AI_REFINER_FAILED: 'AI 修复超时或 API Key 无效，已返回原始 OCR 结果。',
    AI_ALL_PROVIDERS_FAILED: '所有 AI 方案均不可用，请检查方案中心里的 Key、模型名和 Base URL。',
    INVALID_IMAGE: '图片解码失败，请检查图片是否损坏。',
    MISSING_IMAGE: '请求缺少图片数据，请重新上传。',
    BATCH_TOO_LARGE: '批量图片总大小超过限制，请分批上传。',
  }
  return hints[code] || '请重试或查看日志文件了解详情。'
}

const errorDetailJson = computed(() => {
  const err = displayError.value
  if (!err) return ''
  return JSON.stringify({
    code: err.code,
    message: err.message,
    hint: errorHint(err.code),
    file: taskStore.currentTask?.name || '未知',
    time: new Date().toISOString(),
    version: '0.1.0',
  }, null, 2)
})

async function copyError() {
  try {
    await navigator.clipboard.writeText(errorDetailJson.value)
    showToast({ type: 'success', message: '错误信息已复制到剪贴板', duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '复制失败，请手动复制', duration: 3000 })
  }
}

function reportError() {
  const body = encodeURIComponent(
    `**错误报告**\n\n\`\`\`json\n${errorDetailJson.value}\n\`\`\`\n\n请描述你遇到的问题：\n\n复现步骤：\n1. \n2. \n3. \n`
  )
  window.open(`https://github.com/evo-Vonish/vonish-ocr/issues/new?body=${body}`, '_blank')
}

async function startRefine() {
  const result = rawResult.value
  const taskId = taskStore.currentTask?.id
  if (!result || !taskId) return
  activeTab.value = 'polished'
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

async function copyCurrent() {
  const result = rawResult.value
  if (!result) return
  try {
    await copyResult(result, 'polished')
    showToast({ type: 'success', message: '结果已复制到剪贴板', duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '复制失败，请手动复制', duration: 3000 })
  }
}

async function downloadCurrent(format) {
  const result = rawResult.value
  if (!result) return
  await exportSingle(result, taskStore.currentTask?.name || 'ocr-result', exportMode.value, format)
}

function formatConfidence(val) {
  if (val === undefined || val === null) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (Number.isNaN(num)) return '-'
  return `${(num * 100).toFixed(1)}%`
}
</script>

<style scoped>
.result-panel {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--s4);
}

.result-head,
.stream-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s4);
}

.result-kicker,
.result-label,
.error-label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-muted);
  letter-spacing: 0.08em;
}

.result-title {
  margin-top: var(--s1);
  font-size: var(--fs-h2);
  word-break: break-word;
}

.state-tabs,
.export-tabs,
.export-actions,
.stream-actions,
.error-actions {
  display: flex;
  align-items: center;
  gap: var(--s2);
  flex-wrap: wrap;
}

.state-tabs {
  padding: 3px;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.state-tab {
  min-width: 64px;
  height: 34px;
  position: relative;
  border: 0;
  border-radius: var(--r2);
  background: transparent;
  color: var(--v-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  cursor: pointer;
}

.state-tab.active {
  color: var(--v-text);
  background: var(--v-panel);
}

.state-tab.active::after {
  content: "";
  position: absolute;
  left: var(--s2);
  right: var(--s2);
  bottom: 4px;
  height: 1px;
  background: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.result-body {
  min-height: 0;
  flex: 1;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--s4);
}

.result-col,
.single-result,
.error-card,
.loading-card {
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s4);
}

.paper-col {
  background: color-mix(in srgb, var(--v-panel) 82%, var(--v-paper) 18%);
}

.tab-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
}

.result-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding-inline: var(--s2);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-accent);
  background: var(--v-bg);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.ocr-text,
.error-json {
  margin: var(--s3) 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-body);
  font-size: var(--fs-body);
  line-height: 1.85;
  color: var(--v-text);
}

.evidence-text {
  min-height: 520px;
  padding: var(--s5);
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.preprocess-bar,
.confidence-row {
  width: 100%;
  min-height: 36px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--s3);
  margin-top: var(--s3);
  padding: var(--s2) var(--s3);
  background: var(--v-bg);
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.preprocess-thumb {
  display: block;
  width: 100%;
  max-height: 120px;
  object-fit: contain;
  margin-top: var(--s2);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
}

.preprocess-step,
.quiet-note,
.uncertain-box,
.failover-note,
.error-hint {
  margin-top: var(--s3);
  color: var(--v-text-muted);
  font-size: var(--fs-small);
  line-height: 1.6;
}

.failover-note {
  color: var(--v-accent);
  font-family: var(--font-mono);
}

.is-error {
  color: var(--v-error);
}

.diff-list {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  margin-top: var(--s3);
}

.diff-line {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  line-height: 1.7;
}

.diff-arrow {
  color: var(--v-accent);
  margin-inline: var(--s2);
}

.diff-reason {
  margin-left: var(--s3);
  color: var(--v-text-muted);
}

.error-card {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: color-mix(in srgb, var(--v-error-dim) 42%, var(--v-panel) 58%);
  border-color: var(--v-error);
}

.error-title {
  margin-top: var(--s2);
  color: var(--v-error);
  font-size: var(--fs-h2);
  font-weight: var(--fw-semibold);
}

.error-message {
  margin-top: var(--s3);
  color: var(--v-text);
}

.loading-card,
.empty-state {
  min-height: 420px;
  display: grid;
  place-items: center;
  text-align: center;
}

.paper-stage {
  position: relative;
  width: min(520px, 80%);
  min-height: 300px;
  padding: var(--s6);
  overflow: hidden;
  background: var(--v-paper);
  color: var(--v-coal);
  border-radius: var(--r3);
}

.doc-line {
  display: block;
  height: 6px;
  margin-bottom: var(--s4);
  background: color-mix(in srgb, var(--v-coal) 54%, transparent);
  border-radius: var(--r1);
}

.doc-line.wide { width: 78%; }
.doc-line.short { width: 42%; }

.stream-pulse {
  color: var(--v-accent);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.export-panel {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--s3);
  padding-top: var(--s4);
  border-top: 1px solid var(--v-border);
}

.export-panel.disabled {
  opacity: 0.58;
}

/* .export-btn 样式由 global-buttons.css 统一覆盖 */

@media (max-width: 900px) {
  .result-head,
  .stream-head,
  .export-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }

  .export-tabs,
  .export-actions {
    flex-wrap: wrap;
    gap: var(--s1);
  }
}

@media (max-width: 500px) {
  .state-tabs { flex-wrap: wrap; gap: var(--s1); }
  .state-tab { padding-inline: var(--s2); min-height: 32px; font-size: 11px; }
  .ocr-text { font-size: var(--font-small); }
  .result-col,
  .single-result { padding: var(--s3); }
}
</style>
