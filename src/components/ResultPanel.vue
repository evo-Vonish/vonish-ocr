<template>
  <div class="result-panel">
    <div class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 错误卡片 -->
    <div v-if="displayError" class="error-card">
      <div class="error-title">❌ 识别失败</div>
      <div class="error-message">{{ displayError.message }}</div>
      <div class="error-hint">{{ errorHint(displayError.code) }}</div>
    </div>

    <!-- Loading 状态 -->
    <div v-else-if="isLoading" class="loading-card">
      <div class="loading-spinner"></div>
      <div class="loading-text">正在识别中...</div>
    </div>

    <div v-else class="content">
      <div v-if="activeTab === 'raw'" class="tab-pane">
        <div class="meta">置信度: {{ formatConfidence(displayResult.confidence) }}</div>
        <!-- 预处理信息 -->
        <div v-if="preprocessInfo && preprocessInfo.scene" class="preprocess-bar" @click="showPreprocessDetail = !showPreprocessDetail">
          <span class="preprocess-summary">{{ formatPreprocessSummary(preprocessInfo) }}</span>
          <span class="preprocess-toggle">{{ showPreprocessDetail ? '▲' : '▼' }}</span>
        </div>
        <div v-if="showPreprocessDetail && preprocessInfo && preprocessInfo.steps.length" class="preprocess-detail">
          <div v-for="(step, i) in preprocessInfo.steps" :key="i" class="preprocess-step">
            {{ i + 1 }}. {{ step }}
          </div>
        </div>
        <pre class="text-block">{{ displayResult.text || '暂无识别结果' }}</pre>
      </div>

      <div v-if="activeTab === 'polished'" class="tab-pane">
        <div class="meta">AI 置信度: {{ displayResult.aiConfidence }}</div>
        <pre class="text-block">{{ displayResult.polished || '暂无精修结果' }}</pre>
      </div>

      <div v-if="activeTab === 'diff'" class="tab-pane">
        <div v-if="!displayResult.diff.length" class="empty">无修改记录</div>
        <div v-for="(d, i) in displayResult.diff" :key="i" class="diff-card">
          <div class="original">原文: {{ d.original }}</div>
          <div class="arrow">↓</div>
          <div class="fixed">修改: {{ d.fixed }}</div>
          <div class="reason">理由: {{ d.reason }}</div>
        </div>
      </div>
    </div>

    <div v-if="displayResult.uncertain && displayResult.uncertain.length" class="uncertain-banner">
      ⚠️ 存在 {{ displayResult.uncertain.length }} 处不确定内容，建议人工复核
    </div>

    <!-- 导出按钮组 -->
    <div v-if="hasResult" class="export-bar">
      <button class="export-btn" @click="copyToClipboard" title="复制到剪贴板">📋 复制</button>
      <button class="export-btn" @click="exportTXT" title="导出为 TXT">📝 TXT</button>
      <button class="export-btn" @click="exportJSON" title="导出为 JSON">📊 JSON</button>
      <button class="export-btn" @click="exportMarkdown" title="导出为 Markdown">🖊️ MD</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()

const tabs = [
  { key: 'raw', label: '原始 OCR' },
  { key: 'polished', label: 'AI 精修' },
  { key: 'diff', label: '修改记录' },
]
const activeTab = ref('raw')
const showPreprocessDetail = ref(false)

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

const rawResult = computed(() => {
  const current = taskStore.currentTask
  if (current) {
    return taskStore.getResult(current.id)
  }
  return null
})

const hasResult = computed(() => {
  return rawResult.value && rawResult.value.text
})

const isLoading = computed(() => {
  const current = taskStore.currentTask
  if (!current) return false
  // 当前任务在处理中且还没有结果
  return current.status === 'processing' && !rawResult.value
})

const displayError = computed(() => {
  const current = taskStore.currentTask
  if (current) {
    return taskStore.getError(current.id)
  }
  return null
})

const preprocessInfo = computed(() => {
  const result = rawResult.value
  if (!result) return null
  return {
    scene: result.scene || '',
    steps: result.preprocess_steps || [],
    timeMs: result.preprocess_time_ms || 0,
    usedOriginal: result.preprocess_used_original || false,
  }
})

const displayResult = computed(() => {
  const result = rawResult.value
  if (result) {
    const ai = result.ai || {}
    return {
      text: result.text || '',
      confidence: result.confidence || 0,
      polished: ai.polished || result.text || '',
      aiConfidence: ai.confidence || result.confidence || 0,
      diff: ai.diff || [],
      uncertain: ai.uncertain || [],
    }
  }
  return {
    text: '请上传图片并运行识别...\n(选择左侧文件后点击"开始识别")',
    confidence: 0,
    polished: '',
    aiConfidence: 0,
    diff: [],
    uncertain: [],
  }
})

function formatPreprocessSummary(info) {
  if (!info || !info.scene) return ''
  const sceneName = SCENE_NAMES[info.scene] || info.scene
  const parts = []
  if (info.scene === 'screenshot') {
    return `📱 ${sceneName} · 已跳过预处理`
  }
  if (info.usedOriginal) {
    parts.push(`⚠️ ${sceneName} · 预处理效果不佳，已使用原图`)
  } else {
    parts.push(`📄 ${sceneName}`)
    if (info.timeMs > 0) {
      parts.push(`预处理 ${info.timeMs}ms`)
    }
    // 提取角度信息
    const angleStep = info.steps.find(s => s.startsWith('deskew:') || s.startsWith('auto_rotate:'))
    if (angleStep) {
      const match = angleStep.match(/:(.+)/)
      if (match && match[1] !== '0°') {
        parts.push(`已自动校正倾斜 ${match[1]}`)
      }
    }
  }
  return parts.join(' · ')
}

function errorHint(code) {
  const hints = {
    MODEL_NOT_LOADED: '请先下载并加载 OCR 模型（点击配置 → 模型设置）',
    MODEL_LOAD_ERROR: '模型文件可能损坏，请重新下载',
    OCR_ENGINE_ERROR: '图片格式可能不支持，请尝试 JPG 或 PNG',
    AI_REFINER_FAILED: 'AI 修复超时或 API Key 无效，已返回原始 OCR 结果',
    INVALID_IMAGE: '图片解码失败，请检查图片是否损坏',
    MISSING_IMAGE: '请求缺少图片数据，请重新上传',
  }
  return hints[code] || '请重试或查看日志文件了解详情'
}

function _downloadBlob(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function copyToClipboard() {
  const text = displayResult.value.text
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    // 简单反馈：改变按钮文字 1.5 秒
    const btn = event.target
    const original = btn.textContent
    btn.textContent = '✅ 已复制'
    setTimeout(() => { btn.textContent = original }, 1500)
  } catch (e) {
    console.error('复制失败:', e)
    alert('复制失败，请手动复制')
  }
}

function exportTXT() {
  const result = rawResult.value
  if (!result) return
  const content = result.text || ''
  const filename = taskStore.currentTask?.name?.replace(/\.[^.]+$/, '') || 'ocr-result'
  _downloadBlob(content, `${filename}.txt`, 'text/plain;charset=utf-8')
}

function exportJSON() {
  const result = rawResult.value
  if (!result) return
  const exportData = {
    text: result.text,
    blocks: result.blocks || [],
    confidence: result.confidence,
    scene: result.scene || 'print',
    ai: result.ai || null,
    time_ms: result.time_ms || 0,
    exported_at: new Date().toISOString(),
  }
  const content = JSON.stringify(exportData, null, 2)
  const filename = taskStore.currentTask?.name?.replace(/\.[^.]+$/, '') || 'ocr-result'
  _downloadBlob(content, `${filename}.json`, 'application/json')
}

function exportMarkdown() {
  const result = rawResult.value
  if (!result) return
  const filename = taskStore.currentTask?.name?.replace(/\.[^.]+$/, '') || 'image'
  const confidence = formatConfidence(result.confidence)
  const text = result.text || '（无识别结果）'
  const ai = result.ai || {}
  let md = `# OCR 识别结果\n\n`
  md += `**来源**: ${filename}\n\n`
  md += `**置信度**: ${confidence}\n\n`
  md += `**识别时间**: ${result.time_ms || 0}ms\n\n`
  md += `---\n\n`
  md += `## 识别文本\n\n\`\`\`\n${text}\n\`\`\`\n\n`
  if (ai.polished && ai.polished !== text) {
    md += `## AI 精修\n\n\`\`\`\n${ai.polished}\n\`\`\`\n\n`
    if (ai.diff && ai.diff.length) {
      md += `### 修改记录\n\n`
      for (const d of ai.diff) {
        md += `- **原文**: ${d.original || '-'}\n`
        md += `  **修改**: ${d.fixed || '-'}\n`
        if (d.reason) md += `  **理由**: ${d.reason}\n`
        md += `\n`
      }
    }
  }
  _downloadBlob(md, `${filename}.md`, 'text/markdown;charset=utf-8')
}

function formatConfidence(val) {
  if (val === undefined || val === null) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(1) + '%'
}
</script>

<style scoped>
.result-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.tabs {
  display: flex;
  border-bottom: 1px solid #e5e5e5;
  flex-shrink: 0;
}
.tabs button {
  flex: 1;
  padding: 14px;
  background: #fff;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 13px;
  color: #8e8e93;
  transition: all 0.15s;
}
.tabs button.active {
  color: #1a1a2e;
  border-bottom-color: #1a1a2e;
  font-weight: 600;
}
.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
.tab-pane {
  height: 100%;
}
.text-block {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f9f9fb;
  padding: 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.7;
  color: #333;
}
.meta {
  font-size: 12px;
  color: #8e8e93;
  margin-bottom: 10px;
}
.empty {
  color: #c7c7cc;
  text-align: center;
  padding: 60px 20px;
  font-size: 14px;
}
.diff-card {
  padding: 14px;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  margin-bottom: 10px;
  background: #fafafa;
}
.original {
  color: #8e8e93;
  text-decoration: line-through;
  font-size: 13px;
}
.arrow {
  color: #c7c7cc;
  font-size: 12px;
  margin: 4px 0;
}
.fixed {
  color: #1a1a2e;
  font-weight: 600;
  font-size: 14px;
}
.reason {
  color: #666;
  font-size: 12px;
  margin-top: 6px;
}
.uncertain-banner {
  background: #fffbe6;
  border-top: 1px solid #ffe58f;
  padding: 12px 20px;
  font-size: 13px;
  color: #ad8b00;
  flex-shrink: 0;
}
.export-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e5e5e5;
  background: #fafafa;
  flex-shrink: 0;
}
.export-btn {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #d1d1d6;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #333;
  transition: all 0.15s;
}
.export-btn:hover {
  border-color: #1a1a2e;
  background: #f2f2f7;
}
.error-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  text-align: center;
  background: #fff0f0;
}
.error-title {
  font-size: 18px;
  font-weight: 600;
  color: #d32f2f;
  margin-bottom: 12px;
}
.error-message {
  font-size: 14px;
  color: #555;
  margin-bottom: 8px;
  max-width: 400px;
}
.error-hint {
  font-size: 12px;
  color: #888;
  max-width: 400px;
  line-height: 1.5;
}
.preprocess-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f0f7ff;
  border: 1px solid #d6e9ff;
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  font-size: 12px;
  color: #1a6db5;
  transition: background 0.15s;
}
.preprocess-bar:hover {
  background: #e0f0ff;
}
.preprocess-summary {
  flex: 1;
}
.preprocess-toggle {
  font-size: 10px;
  margin-left: 8px;
  color: #7fb3e0;
}
.preprocess-detail {
  background: #f9fbfd;
  border: 1px solid #e8f0f8;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 10px;
}
.preprocess-step {
  font-size: 11px;
  color: #5a7a99;
  padding: 2px 0;
  font-family: 'SF Mono', Monaco, monospace;
}
.loading-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 60px 20px;
  gap: 16px;
}
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e5e5;
  border-top-color: #1a1a2e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.loading-text {
  font-size: 14px;
  color: #8e8e93;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
