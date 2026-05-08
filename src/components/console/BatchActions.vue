<template>
  <div v-if="selectedIds.length" class="batch-actions">
    <span class="mono">SELECTED {{ selectedIds.length }}</span>
    <button class="secondary-btn" type="button" @click="$emit('cancel-selected')">取消选中</button>
    <button class="secondary-btn" type="button" @click="$emit('retry-selected')">批量重试</button>
    <button class="secondary-btn" type="button" @click="$emit('clear-selection')">清除选择</button>
  </div>
</template>

<script setup>
defineProps({
  selectedIds: { type: Array, default: () => [] },
})

defineEmits(['cancel-selected', 'retry-selected', 'clear-selection'])
</script>

<style scoped>
.batch-actions {
  display: flex;
  align-items: center;
  gap: var(--s2);
  padding-top: var(--s3);
  border-top: 1px solid var(--v-border);
}
</style>
