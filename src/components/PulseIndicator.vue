<template>
  <span class="pulse-indicator" :class="state" aria-hidden="true"></span>
</template>

<script setup>
defineProps({
  state: { type: String, default: 'waiting' },
})
</script>

<style scoped>
.pulse-indicator {
  width: 10px;
  height: 10px;
  display: inline-block;
  border: 1px solid var(--v-border-strong);
  border-radius: 50%;
}

.pulse-indicator.running {
  background: var(--v-accent);
  border-color: var(--v-accent);
  animation: v-status-running 1500ms var(--ease-cut) infinite;
}

.pulse-indicator.waiting {
  background: transparent;
  animation: v-status-waiting 2000ms var(--ease-cut) infinite;
}

.pulse-indicator.error {
  background: var(--v-error);
  border-color: var(--v-error);
  animation: v-status-error 300ms linear infinite;
}
</style>
