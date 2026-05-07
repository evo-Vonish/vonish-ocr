<template>
  <div class="oobe-step-ready">
    <div class="oobe-glow-wrap" :class="{ 'is-zooming': isZooming }">
      <div class="oobe-glow-circle"></div>
    </div>
    <h1 class="oobe-ready-title">{{ t('oobe_ready_title') }}</h1>
    <p class="oobe-ready-subtitle">{{ t('oobe_ready_subtitle') }}</p>
    <button class="oobe-ready-btn" @click="enterDesk">{{ t('oobe_ready_enter') }}</button>
  </div>
</template>

<script setup>
import { inject, ref } from 'vue'
import { t } from '../i18n'

const oobeFinish = inject('oobeFinish')
const isZooming = ref(false)

function enterDesk() {
  isZooming.value = true
  setTimeout(() => {
    oobeFinish()
  }, 600)
}
</script>

<style scoped>
.oobe-step-ready {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--s8) 0;
  min-height: 320px;
}

.oobe-glow-wrap {
  margin-bottom: var(--s6);
  transition: transform 600ms var(--ease-cut), opacity 600ms var(--ease-cut);
}

.oobe-glow-wrap.is-zooming {
  transform: scale(3);
  opacity: 0;
}

.oobe-glow-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--v-accent);
  box-shadow:
    0 0 40px var(--v-accent-32),
    0 0 80px var(--v-accent-16);
  animation: oobe-pulse 2s ease-in-out infinite;
}

@keyframes oobe-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.6;
  }
}

.oobe-ready-title {
  font-family: var(--font-title);
  font-size: var(--fs-display);
  font-weight: var(--fw-bold);
  color: var(--v-text);
  line-height: 1.18;
  margin-bottom: var(--s2);
}

.oobe-ready-subtitle {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  line-height: 1.6;
  margin-bottom: var(--s8);
}

.oobe-ready-btn {
  width: 100%;
  max-width: 280px;
  height: 48px;
  background: var(--v-accent-dim);
  border: 1px solid var(--v-accent);
  border-radius: var(--r3);
  color: var(--v-accent);
  font-family: var(--font-body);
  font-size: var(--fs-body);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  transition: all var(--dur-base) var(--ease-cut);
  box-shadow: var(--glow-soft);
}

.oobe-ready-btn:hover {
  background: var(--v-accent);
  color: var(--v-coal);
  box-shadow: var(--glow-active);
}
</style>
