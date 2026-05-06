<template>
  <span class="animated-counter" :class="{ bumping }">{{ displayValue }}</span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  value: { type: [Number, String], required: true },
  pad: { type: Number, default: 0 },
})

const displayValue = computed(() => {
  const raw = String(props.value)
  return props.pad ? raw.padStart(props.pad, '0') : raw
})

const bumping = ref(false)
watch(() => props.value, () => {
  bumping.value = false
  requestAnimationFrame(() => {
    bumping.value = true
    window.setTimeout(() => { bumping.value = false }, 520)
  })
})
</script>

<style scoped>
.animated-counter {
  display: inline-block;
  font-family: var(--font-mono);
  color: currentColor;
}

.animated-counter.bumping {
  animation: counterRoll 500ms var(--ease-cut);
}

@keyframes counterRoll {
  from { opacity: 0; transform: translateY(100%); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
