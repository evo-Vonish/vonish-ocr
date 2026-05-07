<template>
  <div class="empty-vault">
    <div class="empty-icon">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="10" y="8" width="28" height="32" rx="3" stroke="currentColor" stroke-width="1"/>
        <rect x="14" y="12" width="20" height="14" rx="1" stroke="currentColor" stroke-width="1"/>
        <line x1="14" y1="30" x2="30" y2="30" stroke="currentColor" stroke-width="1"/>
        <line x1="14" y1="34" x2="26" y2="34" stroke="currentColor" stroke-width="1"/>
      </svg>
    </div>
    <h2 class="empty-title">暂无归档证据</h2>
    <p class="empty-desc">识别过的文件将自动归档至此，原文件删除后仍可追溯。</p>
    <button class="empty-btn" type="button" @click="$emit('go-desk')">前往证据桌</button>
  </div>
</template>

<script setup>
defineEmits(['go-desk'])
</script>

<style scoped>
.empty-vault {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
  gap: var(--s3);
}

.empty-icon { color: var(--v-text-faint); margin-bottom: var(--s3); }

.empty-title {
  font-family: var(--font-title);
  font-size: 22px;
  color: var(--v-text);
  font-weight: 600;
}

.empty-desc {
  font-size: 13px;
  color: var(--v-text-muted);
  max-width: 360px;
  line-height: 1.6;
}

.empty-btn {
  margin-top: var(--s3);
  height: 38px;
  padding-inline: var(--s5);
  background: var(--v-accent);
  color: var(--v-coal);
  border: 1px solid var(--v-accent);
  border-radius: var(--r3);
  font-size: 14px;
  cursor: pointer;
}
</style>
