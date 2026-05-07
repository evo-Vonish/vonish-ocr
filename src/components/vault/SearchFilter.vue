<template>
  <div class="search-filter">
    <input class="search-input" type="text" placeholder="搜索文件名、文本内容..." :value="search" @input="$emit('update:search', $event.target.value)" />
    <div class="filter-chips">
      <button v-for="f in sceneFilters" :key="f.key" class="filter-chip" :class="{ active: filters.scene_type === f.key }" @click="toggle('scene_type', f.key)">{{ f.label }}</button>
      <span class="chip-sep"></span>
      <button v-for="f in statusFilters" :key="f.key" class="filter-chip" :class="{ active: filters.status === f.key }" @click="toggle('status', f.key)">{{ f.label }}</button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  search: { type: String, default: '' },
  filters: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:search', 'update:filters'])

const sceneFilters = [
  { key: '', label: '全部场景' },
  { key: 'printed_document', label: '印刷' },
  { key: 'handwritten_note', label: '手写' },
  { key: 'screenshot', label: '截屏' },
]
const statusFilters = [
  { key: '', label: '全部状态' },
  { key: 'complete', label: '完成' },
  { key: 'failed', label: '失败' },
]

function toggle(field, key) {
  emit('update:filters', { ...props.filters, [field]: props.filters[field] === key ? '' : key })
}
</script>

<style scoped>
.search-filter { display: flex; align-items: center; gap: var(--s2); }

.search-input {
  width: 180px;
  height: 32px;
  padding-inline: var(--s2);
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text);
  font-size: var(--fs-caption);
}

.search-input::placeholder { color: var(--v-text-faint); }

.filter-chips { display: flex; align-items: center; gap: 4px; }

.chip-sep { width: 1px; height: 16px; background: var(--v-border); margin-inline: 2px; }

.filter-chip {
  height: 28px;
  padding-inline: var(--s2);
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text-muted);
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s, color 0.15s;
}

.filter-chip:hover { border-color: var(--v-border-strong); color: var(--v-text); }

.filter-chip.active { border-color: var(--v-accent); color: var(--v-accent); box-shadow: var(--glow-soft); }
</style>
