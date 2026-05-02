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

    <div class="content">
      <div v-if="activeTab === 'raw'" class="tab-pane">
        <div class="meta">置信度: {{ displayResult.confidence }}</div>
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

const displayResult = computed(() => {
  const current = taskStore.currentTask
  if (current) {
    const result = taskStore.getResult(current.id)
    if (result) return result
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
</style>
