<template>
  <div class="oobe-step">
    <h1 class="oobe-step-title">{{ t('oobe_tutorial_title') }}</h1>
    <p class="oobe-step-subtitle">{{ t('oobe_tutorial_subtitle') }}</p>

    <div class="oobe-tutor-stage">
      <div class="oobe-tutor-demo">
        <div class="oobe-tutor-highlight" :class="`step-${currentTip}`">
          <div class="oobe-tutor-topbar">VonishOCR</div>
          <div class="oobe-tutor-body">
            <div class="oobe-tutor-left">QUEUE</div>
            <div class="oobe-tutor-center">
              <span v-if="currentTip === 1">INGEST</span>
              <span v-else-if="currentTip === 2">MODEL</span>
              <span v-else-if="currentTip === 3" class="dashed">CONFIDENCE</span>
              <span v-else>RESULT</span>
            </div>
            <div class="oobe-tutor-right">AUDIT</div>
          </div>
        </div>
      </div>
      <p class="oobe-tutor-desc">{{ currentDesc }}</p>
    </div>

    <div class="oobe-tutor-dots">
      <div
        v-for="n in 4"
        :key="n"
        class="oobe-tutor-dot"
        :class="{ 'is-active': n === currentTip }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { t } from '../i18n'

const currentTip = ref(1)

const tips = computed(() => [
  { title: t('oobe_tutorial_step1_title'), desc: t('oobe_tutorial_step1_desc') },
  { title: t('oobe_tutorial_step2_title'), desc: t('oobe_tutorial_step2_desc') },
  { title: t('oobe_tutorial_step3_title'), desc: t('oobe_tutorial_step3_desc') },
  { title: t('oobe_tutorial_step4_title'), desc: t('oobe_tutorial_step4_desc') }
])

const currentDesc = computed(() => tips.value[currentTip.value - 1]?.desc || '')

function nextTip() {
  if (currentTip.value < 4) {
    currentTip.value++
  }
}

defineExpose({ nextTip, currentTip })
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

.oobe-tutor-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s4);
  margin-bottom: var(--s6);
}

.oobe-tutor-demo {
  width: 100%;
  max-width: 400px;
  aspect-ratio: 16 / 10;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  overflow: hidden;
  padding: var(--s4);
}

.oobe-tutor-highlight {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  overflow: hidden;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-tutor-highlight.step-1 .oobe-tutor-center {
  border-color: var(--v-accent);
  box-shadow: inset 0 0 12px var(--v-accent-16);
}

.oobe-tutor-highlight.step-2 .oobe-tutor-left {
  border-color: var(--v-accent);
  box-shadow: inset 0 0 12px var(--v-accent-16);
}

.oobe-tutor-highlight.step-3 .oobe-tutor-right {
  border-color: var(--v-accent);
  box-shadow: inset 0 0 12px var(--v-accent-16);
}

.oobe-tutor-highlight.step-4 .oobe-tutor-right {
  border-color: var(--v-accent);
  box-shadow: inset 0 0 12px var(--v-accent-16);
}

.oobe-tutor-topbar {
  height: 20px;
  background: var(--v-rail);
  border-bottom: 1px solid var(--v-border);
  display: flex;
  align-items: center;
  padding: 0 6px;
  font-family: var(--font-mono);
  font-size: 7px;
  color: var(--v-text-muted);
}

.oobe-tutor-body {
  flex: 1;
  display: grid;
  grid-template-columns: 40px 1fr 36px;
  gap: 3px;
  padding: 3px;
}

.oobe-tutor-left,
.oobe-tutor-center,
.oobe-tutor-right {
  border: 1px solid var(--v-border);
  border-radius: var(--r1);
  display: grid;
  place-items: center;
  font-family: var(--font-mono);
  font-size: 7px;
  color: var(--v-text-muted);
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-tutor-left {
  background: var(--v-rail);
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.oobe-tutor-center {
  background: var(--v-panel);
}

.oobe-tutor-center .dashed {
  border: 1px dashed var(--v-accent);
  padding: 2px 4px;
  border-radius: var(--r1);
}

.oobe-tutor-right {
  background: var(--v-rail);
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.oobe-tutor-desc {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  color: var(--v-text);
  text-align: center;
  line-height: 1.6;
  max-width: 400px;
}

.oobe-tutor-dots {
  display: flex;
  gap: var(--s3);
  justify-content: center;
}

.oobe-tutor-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid var(--v-border);
  background: transparent;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-tutor-dot.is-active {
  background: var(--v-accent);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}
</style>
