<template>
  <Teleport to="body">
    <TransitionGroup name="dialog">
      <div
        v-for="dialog in dialogs"
        :key="dialog.id"
        class="dialog-overlay"
        @click.self="cancelDialog(dialog.id)"
      >
        <div class="dialog-panel">
          <div class="dialog-head">
            <span class="dialog-title">{{ dialog.title }}</span>
          </div>
          <div class="dialog-body">{{ dialog.message }}</div>
          <div class="dialog-foot">
            <button
              v-if="dialog.type === 'confirm'"
              class="dialog-btn secondary"
              type="button"
              @click="cancelDialog(dialog.id)"
            >
              {{ dialog.cancelText }}
            </button>
            <button
              class="dialog-btn primary"
              type="button"
              @click="confirmDialog(dialog.id)"
            >
              {{ dialog.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { useDialog } from '../composables/useDialog'

const { dialogs, confirmDialog, cancelDialog } = useDialog()
</script>

<style>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 17, 15, 0.72);
  z-index: 10000;
  display: grid;
  place-items: center;
  padding: var(--s5);
}

.dialog-panel {
  width: 100%;
  max-width: 400px;
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding: var(--s5);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
}

.dialog-head {
  margin-bottom: var(--s3);
}

.dialog-title {
  font-family: var(--font-title);
  font-size: var(--fs-h2);
  color: var(--v-text);
}

.dialog-body {
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  line-height: 1.6;
  margin-bottom: var(--s5);
  word-break: break-word;
}

.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--s3);
}

.dialog-btn {
  min-height: 36px;
  padding-inline: var(--s4);
  border-radius: var(--r3);
  font-size: var(--fs-small);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  transition: all var(--dur-base) var(--ease-cut);
}

.dialog-btn.primary {
  background: var(--v-accent);
  color: var(--v-coal);
  border: 0;
}

.dialog-btn.primary:hover {
  box-shadow: var(--glow-soft);
}

.dialog-btn.secondary {
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
}

.dialog-btn.secondary:hover {
  color: var(--v-text);
  border-color: var(--v-border-strong);
}

.dialog-enter-active,
.dialog-leave-active {
  transition: all var(--dur-base) var(--ease-cut);
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog-panel,
.dialog-leave-to .dialog-panel {
  opacity: 0;
  transform: scale(0.96);
}

.dialog-enter-active .dialog-panel,
.dialog-leave-active .dialog-panel {
  transition: all var(--dur-base) var(--ease-cut);
}
</style>
