<template>
  <span class="focus-ring" aria-hidden="true"></span>
</template>

<script setup>
defineOptions({ name: 'FocusRing' })
</script>

<style scoped>
.focus-ring {
  pointer-events: none;
  position: absolute;
  inset: calc(-1 * var(--v-focus-offset));
  border: 2px solid var(--v-focus);
  border-radius: inherit;
  opacity: 0;
  transition: opacity 150ms ease;
}

:focus-visible > .focus-ring {
  opacity: 1;
}

[data-theme-style="hc"] .focus-ring {
  border-radius: 0;
}
</style>
