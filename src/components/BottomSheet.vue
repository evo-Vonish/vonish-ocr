<template>
  <Teleport to="body">
    <div v-if="visible" class="bottom-sheet-backdrop" @click="close" />
    <div class="bottom-sheet" :class="{ open: visible }" :style="{ height: sheetHeight }">
      <div class="sheet-handle" @click="close">
        <span class="handle-bar"></span>
      </div>
      <div class="sheet-content">
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  height: { type: String, default: '70vh' },
})
const emit = defineEmits(['close'])

const sheetHeight = props.height

function close() {
  emit('close')
}
</script>

<style scoped>
.bottom-sheet-backdrop {
  position: fixed;
  inset: 0;
  z-index: 99;
  background: color-mix(in srgb, var(--v-bg) 60%, transparent);
  animation: backdrop-in 0.3s ease;
}

@keyframes backdrop-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  border-radius: 16px 16px 0 0;
  background: var(--v-rail);
  border: 1px solid var(--v-border-strong);
  border-bottom: none;
  box-shadow: 0 -4px 32px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.2, 0, 0.1, 1);
  max-height: 90vh;
}

.bottom-sheet.open {
  transform: translateY(0);
}

.sheet-handle {
  display: flex;
  justify-content: center;
  padding: var(--space-sm) 0;
  cursor: pointer;
  flex-shrink: 0;
}

.handle-bar {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--v-border-strong);
}

.sheet-content {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 0 var(--space-md) var(--space-lg);
  -webkit-overflow-scrolling: touch;
}
</style>
