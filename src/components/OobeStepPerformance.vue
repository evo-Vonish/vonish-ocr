<template>
  <div class="oobe-step">
    <h1 class="oobe-step-title">{{ t('oobe_perf_title') }}</h1>
    <p class="oobe-step-subtitle">{{ t('oobe_perf_subtitle') }}</p>

    <div class="oobe-perf-list">
      <div
        v-for="p in profiles"
        :key="p.key"
        class="v-card oobe-perf-card"
        :class="{ 'is-active': oobeData.performance === p.key }"
        @click="selectPerf(p.key)"
      >
        <div class="oobe-perf-header">
          <span class="oobe-perf-name">{{ p.label }}</span>
          <span v-if="oobeData.performance === p.key" class="oobe-perf-current">{{ t('oobe_perf_current') }}</span>
        </div>
        <div class="oobe-perf-params">{{ p.params }}</div>
        <div class="oobe-perf-desc">{{ p.desc }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { t } from '../i18n'

const oobeData = inject('oobeData')

const profiles = computed(() => [
  {
    key: 'beast',
    label: t('oobe_perf_beast'),
    params: t('oobe_perf_beast_params'),
    desc: t('oobe_perf_beast_desc')
  },
  {
    key: 'balanced',
    label: t('oobe_perf_balanced'),
    params: t('oobe_perf_balanced_params'),
    desc: t('oobe_perf_balanced_desc')
  },
  {
    key: 'eco',
    label: t('oobe_perf_eco'),
    params: t('oobe_perf_eco_params'),
    desc: t('oobe_perf_eco_desc')
  }
])

function selectPerf(key) {
  oobeData.performance = key
}
</script>

<style scoped>
.oobe-step {
  position: relative;
}

.oobe-step-title {
  font-family: var(--font-title);
  font-size: var(--fs-display);
  font-weight: var(--fw-bold);
  color: var(--v-text);
  line-height: 1.18;
  margin-bottom: var(--s2);
}

.oobe-step-subtitle {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  line-height: 1.6;
  margin-bottom: var(--s6);
}

.oobe-perf-list {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}

.oobe-perf-card {
  padding: var(--s4);
  position: relative;
  overflow: hidden;
  cursor: pointer;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-perf-card.is-active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-active);
}

.oobe-perf-card.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--v-accent);
  animation: oobe-perf-line-in var(--dur-base) var(--ease-cut) forwards;
}

@keyframes oobe-perf-line-in {
  from { transform: scaleY(0); }
  to { transform: scaleY(1); }
}

.oobe-perf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--s1);
}

.oobe-perf-name {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  font-weight: var(--fw-semibold);
  color: var(--v-text);
}

.oobe-perf-current {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--v-accent);
  letter-spacing: 0.04em;
}

.oobe-perf-params {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  margin-bottom: var(--s1);
}

.oobe-perf-desc {
  font-family: var(--font-body);
  font-size: var(--fs-small);
  color: var(--v-text-muted);
}
</style>
