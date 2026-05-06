<template>
  <div class="skeleton-loader" :class="variant">
    <span v-if="variant === 'thumb'" class="skeleton-thumb"></span>
    <template v-else>
      <span v-for="i in lines" :key="i" class="skeleton-line" :style="{ width: widths[(i - 1) % widths.length] }"></span>
    </template>
  </div>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'text' },
  lines: { type: Number, default: 4 },
})

const widths = ['78%', '64%', '82%', '42%']
</script>

<style scoped>
.skeleton-loader {
  display: grid;
  gap: var(--s2);
}

.skeleton-line {
  height: 10px;
  border-radius: var(--r1);
}

.skeleton-thumb {
  width: 48px;
  height: 48px;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
}
</style>
