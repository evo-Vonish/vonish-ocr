<template>
  <button class="queue-task-row" type="button" :class="{ selected }" @click="$emit('toggle', task.id)">
    <span class="mono">#{{ shortId }}</span>
    <span class="task-name">{{ task.filename }}</span>
    <span class="mono">{{ task.model_tier || 'auto' }}</span>
    <span class="task-status" :class="task.status">
      <i aria-hidden="true"></i>{{ statusText }}
    </span>
    <span class="mono">{{ elapsedText }}</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

defineEmits(['toggle'])

const shortId = computed(() => String(props.task.id || '').slice(0, 8))
const elapsedText = computed(() => props.task.elapsed_ms ? `${props.task.elapsed_ms}ms` : '--')
const statusText = computed(() => ({
  queued: 'WAITING',
  processing: 'OCR',
  preprocess: 'PREPROCESS',
  refine: 'REFINE',
  done: 'DONE',
  failed: 'FAILED',
  cancelled: 'CANCELLED',
}[props.task.status] || String(props.task.status || 'WAITING').toUpperCase()))
</script>

<style scoped>
.queue-task-row {
  width: 100%;
  display: grid;
  grid-template-columns: 78px minmax(0, 1.4fr) 86px 116px 70px;
  align-items: center;
  gap: var(--s2);
  min-height: 34px;
  border: 1px solid transparent;
  border-bottom-color: var(--v-border);
  background: transparent;
  color: var(--v-text-muted);
  text-align: left;
  font-family: var(--font-body);
  cursor: pointer;
}

.queue-task-row:hover,
.queue-task-row.selected {
  border-color: var(--v-accent);
  background: var(--v-accent-08);
}

.task-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--v-text);
}

.task-status {
  display: inline-flex;
  align-items: center;
  gap: var(--s2);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.task-status i {
  width: 8px;
  height: 8px;
  border: 1px solid var(--v-border);
  border-radius: 50%;
}

.task-status.processing i,
.task-status.preprocess i,
.task-status.refine i {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
  animation: task-pulse 1.5s var(--ease-cut) infinite;
}

.task-status.done {
  color: var(--v-accent);
}

.task-status.done i {
  background: var(--v-accent);
  border-color: var(--v-accent);
}

.task-status.failed,
.task-status.cancelled {
  color: var(--v-error);
}

.task-status.failed i,
.task-status.cancelled i {
  background: var(--v-error);
  border-color: var(--v-error);
}

@keyframes task-pulse {
  0%, 100% { transform: scale(1); opacity: 0.68; }
  50% { transform: scale(1.35); opacity: 1; }
}
</style>
