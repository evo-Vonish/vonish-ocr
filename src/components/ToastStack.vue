<template>
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="toast.type"
          @click="dismissToast(toast.id)"
        >
          <span class="toast-icon">{{ iconFor(toast.type) }}</span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" @click.stop="dismissToast(toast.id)">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast, dismissToast } from '../composables/useToast'

const { toasts } = useToast()

function iconFor(type) {
  const map = { error: '✕', warning: '▲', success: '✓', info: 'ℹ' }
  return map[type] || '•'
}
</script>

<style>
.toast-stack {
  position: fixed;
  top: calc(var(--topbar-h) + var(--s3));
  right: var(--s4);
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  max-width: 380px;
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: var(--s2);
  padding: var(--s3) var(--s4);
  border-radius: var(--r3);
  font-size: var(--fs-small);
  line-height: 1.4;
  color: var(--v-text);
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  pointer-events: auto;
  cursor: pointer;
  transition: opacity var(--dur-base) var(--ease-cut);
}

.toast-item:hover {
  opacity: 0.92;
}

.toast-item.error {
  border-left: 3px solid var(--v-error);
}

.toast-item.warning {
  border-left: 3px solid var(--v-format);
}

.toast-item.success {
  border-left: 3px solid var(--v-insert);
}

.toast-item.info {
  border-left: 3px solid var(--v-accent);
}

.toast-icon {
  font-size: var(--fs-body);
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-close {
  background: none;
  border: none;
  color: var(--v-text-faint);
  font-size: 18px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  transition: color var(--dur-base) var(--ease-cut);
}

.toast-close:hover {
  color: var(--v-text);
}

.toast-enter-active,
.toast-leave-active {
  transition: all var(--dur-base) var(--ease-cut);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
