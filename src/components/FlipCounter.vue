<template>
  <span class="fc-root">
    <span
      v-for="(digit, i) in digits"
      :key="i"
      class="fc-digit"
      :class="{ flip: flippedIndices.has(i) }"
    >{{ digit }}</span>
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  pad: { type: Number, default: 2 },
})

const flippedIndices = ref(new Set())

const digits = computed(() =>
  String(props.value).padStart(props.pad, '0').split('')
)

watch(() => props.value, (newVal, oldVal) => {
  if (oldVal === undefined) return
  const a = String(newVal).padStart(props.pad, '0')
  const b = String(oldVal).padStart(props.pad, '0')
  const changed = new Set()
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) changed.add(i)
  }
  if (changed.size > 0) {
    flippedIndices.value = changed
    setTimeout(() => flippedIndices.value = new Set(), 400)
  }
})
</script>

<style scoped>
.fc-root {
  display: inline-flex;
  gap: 1px;
}

.fc-digit {
  display: inline-block;
  transition: filter 0.3s ease, opacity 0.3s ease, transform 0.3s ease;
}

.fc-digit.flip {
  animation: fc-flip 0.4s ease;
}

@keyframes fc-flip {
  0%   { filter: blur(4px); opacity: 0; transform: translateY(-6px); }
  40%  { filter: blur(2px); opacity: 0.3; transform: translateY(0); }
  100% { filter: blur(0); opacity: 1; transform: translateY(0); }
}
</style>
