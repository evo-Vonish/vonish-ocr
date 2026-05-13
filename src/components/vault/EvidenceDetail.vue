<template>
  <div class="detail-panel">
    <div class="detail-head">
      <div class="detail-label">EVIDENCE DETAIL</div>
      <button class="close-btn" type="button" @click="$emit('close')">×</button>
    </div>

    <div class="detail-thumb">
      <img v-if="assetUrl(evidence.original_url || evidence.original_copy_path)" :src="assetUrl(evidence.original_url || evidence.original_copy_path)" alt="" />
      <div v-else class="no-preview">NO PREVIEW</div>
    </div>

    <div class="detail-info">
      <div class="info-row"><span>文件名</span><b>{{ evidence.filename }}</b></div>
      <div class="info-row"><span>大小</span><b>{{ formatSize(evidence.file_size) }}</b></div>
      <div class="info-row"><span>场景</span><b>{{ evidence.scene_type || '--' }}</b></div>
      <div class="info-row"><span>模型</span><b>{{ evidence.model_tier || '--' }}</b></div>
      <div class="info-row"><span>置信度</span><b class="accent">{{ formatConf(evidence.ocr_confidence) }}</b></div>
      <div class="info-row"><span>耗时</span><b>{{ evidence.process_time_ms || '--' }}ms</b></div>
      <div class="info-row"><span>状态</span><b :class="evidence.status">{{ statusText(evidence.status) }}</b></div>
    </div>

    <div class="detail-tabs">
      <button :class="{ active: tab === 'raw' }" type="button" @click="tab = 'raw'">原始</button>
      <button :class="{ active: tab === 'refined' }" type="button" @click="tab = 'refined'">精修</button>
      <button :class="{ active: tab === 'diff' }" type="button" @click="tab = 'diff'">Diff</button>
    </div>

    <div class="detail-text">
      <MdRender v-if="tab === 'raw'" :text="evidence.raw_text || '暂无内容'" />
      <MdRender v-else-if="tab === 'refined'" :text="evidence.refined_text || '暂无精修结果'" />
      <pre v-else>{{ evidence.diff_json || '无差异记录' }}</pre>
    </div>

    <div class="detail-actions">
      <button class="action-btn" type="button" @click="$emit('reprocess')">重新识别</button>
      <button class="action-btn primary" type="button" @click="$emit('export')">导出</button>
      <button class="action-btn" type="button" @click="$emit('move')">移至案卷组</button>
      <button class="action-btn danger" type="button" @click="$emit('delete')">删除</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MdRender from '../MdRender.vue'

const props = defineProps({
  evidence: { type: Object, default: () => ({}) },
  backendBase: { type: String, default: '' },
})
defineEmits(['close', 'reprocess', 'export', 'move', 'delete'])

const tab = ref('raw')

function assetUrl(url) {
  if (!url) return ''
  if (/^(https?:|file:|data:|blob:)/.test(url)) return url
  if (url.startsWith('/')) return `${props.backendBase}${url}`
  return `${props.backendBase}/vault/file/${encodeURI(String(url).replaceAll('\\', '/'))}`
}

function formatSize(b) {
  if (!b) return '--'
  return b < 1048576 ? `${(b / 1024).toFixed(1)}KB` : `${(b / 1048576).toFixed(1)}MB`
}

function formatConf(v) {
  return v != null ? `${(v * 100).toFixed(1)}%` : '--'
}

function statusText(s) {
  return { complete: '完成', failed: '失败', processing: '处理中', needs_review: '待复核' }[s] || s || '--'
}
</script>

<style scoped>
.detail-panel { display: flex; flex-direction: column; gap: var(--s3); height: 100%; }

.detail-head { display: flex; justify-content: space-between; align-items: center; }

.detail-label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-muted);
  letter-spacing: 0.08em;
}

.close-btn {
  width: 24px; height: 24px;
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text);
  cursor: pointer;
}

.detail-thumb {
  width: 100%;
  aspect-ratio: 4/3;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  overflow: hidden;
}

.detail-thumb img { width: 100%; height: 100%; object-fit: contain; }

.no-preview {
  display: grid; place-items: center;
  height: 100%;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-text-faint);
}

.detail-info {
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s3);
  display: flex;
  flex-direction: column;
  gap: var(--s2);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--s2);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.info-row b {
  color: var(--v-text);
  font-family: var(--font-mono);
  font-size: 11px;
  text-align: right;
  word-break: break-all;
}
.info-row .accent { color: var(--v-accent); }
.info-row .failed { color: var(--v-error); }

.detail-tabs {
  display: flex;
  gap: var(--s2);
}

.detail-tabs button {
  min-height: 30px;
  padding-inline: var(--s2);
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
}

.detail-tabs button.active { border-color: var(--v-accent); color: var(--v-text); box-shadow: var(--glow-soft); }

.detail-text {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s3);
}

.detail-text pre {
  font-family: var(--font-body);
  font-size: var(--fs-small);
  color: var(--v-text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s1);
}

.action-btn {
  flex: 1;
  min-height: 32px;
  padding-inline: var(--s2);
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}

.action-btn.primary { background: var(--v-accent); border-color: var(--v-accent); color: var(--v-coal); }
.action-btn.danger { border-color: var(--v-error); color: var(--v-error); }
</style>
