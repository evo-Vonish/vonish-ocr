<template>
  <div class="v-adaptive-card">
    <div v-if="$slots.icon || icon" class="card-icon">
      <slot name="icon">
        <img v-if="icon" :src="icon" :alt="title || ''" />
      </slot>
    </div>
    <div class="card-body">
      <div v-if="title" class="card-title">{{ title }}</div>
      <div v-if="$slots.default || description" class="card-desc">
        <slot>{{ description }}</slot>
      </div>
    </div>
    <div v-if="label || $slots.label" class="card-label">
      <slot name="label">{{ label }}</slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  label: { type: String, default: '' },
})
</script>

<style scoped>
.v-adaptive-card {
  container-type: inline-size;
  display: flex;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--radius-md);
  transition: all 0.3s ease;
  cursor: default;
}

.v-adaptive-card:hover {
  border-color: var(--v-border-strong);
}

.card-title {
  font-family: var(--font-title);
  font-size: var(--font-h2);
  color: var(--v-text);
  margin: 0 0 var(--space-xs);
}

.card-desc {
  font-size: var(--font-small);
  color: var(--v-text-muted);
  line-height: 1.55;
}

.card-label {
  font-family: var(--font-mono);
  font-size: var(--font-caption);
  color: var(--v-text-faint);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

/* ── 宽容器：横排 ── */
@container (min-width: 400px) {
  .v-adaptive-card {
    flex-direction: row;
    align-items: center;
  }
  .card-icon { width: 64px; height: 64px; flex-shrink: 0; }
  .card-icon img { width: 100%; height: 100%; object-fit: contain; }
  .card-body { flex: 1 1 0; }
}

/* ── 中容器：纵排 ── */
@container (min-width: 200px) and (max-width: 399px) {
  .v-adaptive-card {
    flex-direction: column;
    align-items: flex-start;
  }
  .card-icon { width: 48px; height: 48px; }
  .card-icon img { width: 100%; height: 100%; object-fit: contain; }
}

/* ── 窄容器：仅图标+文字 ── */
@container (max-width: 199px) {
  .v-adaptive-card {
    flex-direction: column;
    align-items: center;
    gap: var(--space-xs);
    padding: var(--space-sm);
  }
  .card-icon { width: 32px; height: 32px; }
  .card-icon img { width: 100%; height: 100%; object-fit: contain; }
  .card-body { display: none; }
  .card-label { font-size: var(--font-micro); }
}

/* ── 超窄：纯图标按钮 ── */
@container (max-width: 119px) {
  .v-adaptive-card {
    width: 40px; height: 40px;
    border-radius: 50%;
    padding: 0;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--v-border-strong);
  }
  .card-label { display: none; }
  .card-icon { width: 20px; height: 20px; }
}
</style>
