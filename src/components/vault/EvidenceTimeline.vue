<template>
  <div class="timeline">
    <div v-if="loading" class="timeline-empty">加载中...</div>
    <div v-else-if="!evidences.length" class="timeline-empty">暂无证据</div>
    <div v-else class="timeline-grid">
      <div
        v-for="ev in evidences"
        :key="ev.id"
        class="ev-card"
        :class="{ selected: selectedIds.includes(ev.id) }"
        @click="$emit('toggle', ev.id)"
        @dblclick="$emit('select', ev)"
      >
        <div class="ev-check" :class="{ on: selectedIds.includes(ev.id) }">
          <span v-if="selectedIds.includes(ev.id)">✓</span>
        </div>
        <div class="ev-thumb">
          <div v-if="ev.thumbnail_path" class="thumb-img" :style="{ backgroundImage: `url(/vault-file/${ev.thumbnail_path})` }" />
          <div v-else class="thumb-placeholder">NO IMAGE</div>
        </div>
        <div class="ev-meta">
          <span class="ev-name">{{ ev.filename }}</span>
          <span class="ev-size">{{ formatSize(ev.file_size) }}</span>
          <span class="ev-status" :class="ev.status">
            <span class="status-dot"></span>
            {{ statusText(ev.status) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  evidences: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selectedIds: { type: Array, default: () => [] },
})
defineEmits(['select', 'toggle'])

function formatSize(bytes) {
  if (!bytes) return '--'
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

function statusText(s) {
  return { complete: '完成', failed: '失败', processing: '处理中', needs_review: '待复核' }[s] || s
}
</script>

<style scoped>
.timeline { height: 100%; }

.timeline-empty {
  display: grid; place-items: center;
  height: 200px;
  color: var(--v-text-muted);
  font-size: var(--fs-small);
}

.timeline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--s3);
}

.ev-card {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  position: relative;
}

.ev-card:hover {
  transform: translateY(-2px);
  border-color: var(--v-border-strong);
}

.ev-card.selected {
  border-color: var(--v-accent);
  box-shadow: var(--glow-active);
}

.ev-check {
  position: absolute;
  top: var(--s1); left: var(--s1);
  width: 16px; height: 16px;
  border: 1px solid var(--v-border-strong);
  border-radius: var(--r1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: transparent;
  z-index: 1;
  background: var(--v-rail);
}

.ev-check.on {
  border-color: var(--v-accent);
  color: var(--v-accent);
}

.ev-thumb {
  width: 100%;
  aspect-ratio: 4/3;
  background: var(--v-bg);
  overflow: hidden;
}

.thumb-img {
  width: 100%; height: 100%;
  background-size: cover;
  background-position: center;
}

.thumb-placeholder {
  width: 100%; height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--v-text-faint);
}

.ev-meta {
  padding: var(--s2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ev-name {
  font-size: 12px;
  color: var(--v-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.ev-size {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--v-text-muted);
}

.ev-status {
  font-family: var(--font-mono);
  font-size: 9px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ev-status.complete { color: var(--v-accent); }
.ev-status.failed { color: var(--v-error); }

.status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.ev-status.complete .status-dot { animation: none; }
.ev-status.failed .status-dot { animation: shake 400ms ease-in-out infinite; }

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}
</style>
