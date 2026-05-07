<template>
  <div class="batch-bar">
    <div class="batch-left">
      <span class="batch-count">已选中 {{ count }} 项</span>
      <button class="batch-link" @click="$emit('close')">取消选择</button>
    </div>
    <div class="batch-right">
      <button class="batch-btn" @click="$emit('delete')">批量删除</button>
      <button class="batch-btn" @click="$emit('export')">批量导出</button>
      <button class="batch-btn" @click="$emit('move')">移至案件组</button>
    </div>
  </div>
</template>

<script setup>
defineProps({ count: { type: Number, default: 0 } })
defineEmits(['close', 'delete', 'export', 'move'])
</script>

<style scoped>
.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding-inline: var(--s3);
  background: var(--v-panel-raised);
  border: 1px solid var(--v-accent);
  border-radius: var(--r3);
  margin-bottom: var(--s3);
}

.batch-left { display: flex; align-items: center; gap: var(--s3); }

.batch-count {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
}

.batch-link {
  background: none; border: none;
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
  cursor: pointer;
}

.batch-right { display: flex; gap: var(--s1); }

.batch-btn {
  height: 28px;
  padding-inline: var(--s2);
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text);
  font-size: 11px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.batch-btn:hover { border-color: var(--v-accent); }
</style>
