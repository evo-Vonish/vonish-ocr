<template>
  <div class="empty-state-art">
    <svg class="scan-glyph" viewBox="0 0 120 120" aria-hidden="true">
      <rect x="24" y="18" width="72" height="84" rx="4" />
      <path d="M36 40H84M36 56H78M36 72H88" />
      <line class="scan-line" x1="26" y1="28" x2="94" y2="28" />
    </svg>
    <div class="empty-main">{{ title }}</div>
    <div class="empty-sub">{{ subtitle }}</div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '把第一张废墟放到桌上' },
  subtitle: { type: String, default: '支持 JPG PNG PDF' },
})
</script>

<style scoped>
.empty-state-art {
  position: relative;
  width: min(520px, 100%);
  min-height: 320px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--s3);
  background:
    linear-gradient(var(--v-accent-08) 1px, transparent 1px),
    linear-gradient(90deg, var(--v-accent-08) 1px, transparent 1px);
  background-size: 24px 24px;
  border: 1px dashed var(--v-border);
  border-radius: var(--r4);
}

.scan-glyph {
  width: 88px;
  height: 88px;
  color: var(--v-accent);
}

.scan-glyph rect,
.scan-glyph path,
.scan-glyph line {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
}

.scan-line {
  animation: emptyScan 3000ms var(--ease-cut) infinite;
}

.empty-main {
  font-family: var(--font-title);
  font-size: 24px;
  font-weight: var(--fw-bold);
  color: var(--v-text);
}

.empty-sub {
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

@keyframes emptyScan {
  0%, 100% { transform: translateY(0); opacity: 0.35; }
  50% { transform: translateY(62px); opacity: 1; }
}
</style>
