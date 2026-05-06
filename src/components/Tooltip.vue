<template>
  <span class="tooltip-wrap" @mouseenter="open" @mouseleave="close" @focusin="open" @focusout="close">
    <slot />
    <span v-if="visible" class="tooltip-box" role="tooltip">{{ text }}</span>
  </span>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  text: { type: String, required: true },
})

const visible = ref(false)
let timer = null

function open() {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => { visible.value = true }, 300)
}

function close() {
  window.clearTimeout(timer)
  visible.value = false
}
</script>

<style scoped>
.tooltip-wrap {
  position: relative;
  display: inline-flex;
}

.tooltip-box {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  z-index: 100;
  transform: translate(-50%, 4px);
  min-width: max-content;
  max-width: 240px;
  padding: 6px 10px;
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text);
  font-size: 11px;
  line-height: 1.4;
  box-shadow: var(--glow-soft);
  animation: tooltipIn 150ms var(--ease-cut) forwards;
}

@keyframes tooltipIn {
  from { opacity: 0; transform: translate(-50%, 4px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
</style>
