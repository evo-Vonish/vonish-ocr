<template>
  <div v-if="visible" class="oobe-shell" :class="{ 'is-exiting': isExiting }">
    <div class="oobe-card">
      <Transition :name="transitionName" mode="out-in">
        <component
          :is="currentComponent"
          ref="stepRef"
          :key="currentStep"
        />
      </Transition>

      <!-- Step 5 专用操作区（ENTER THE DESK） -->
      <div v-if="currentStep === 5" class="oobe-ready-actions">
        <button class="oobe-ready-btn" @click="enterTutorial">{{ t('oobe_ready_enter') }}</button>
      </div>

      <!-- Step 6 专用操作区（SKIP / NEXT TIP / FINISH） -->
      <div v-else-if="currentStep === 6" class="oobe-actions">
        <button class="oobe-btn-ghost" @click="skipTutorial">{{ t('oobe_tutorial_skip') }}</button>
        <button class="oobe-btn-primary" @click="tutorialNext">
          {{ tutorialButtonText }}
        </button>
      </div>

      <!-- 通用操作栏（Step 1-4） -->
      <div v-else class="oobe-actions">
        <button
          v-if="currentStep > 1"
          class="oobe-btn-ghost"
          @click="prevStep"
        >
          {{ t('oobe_back') }}
        </button>
        <div v-else></div>
        <button class="oobe-btn-primary" @click="nextStep">
          {{ t('oobe_next') }}
        </button>
      </div>
    </div>

    <!-- 步骤指示器 -->
    <div class="oobe-dots">
      <div
        v-for="n in totalSteps"
        :key="n"
        class="oobe-dot"
        :class="{ 'is-active': n === currentStep, 'is-done': n < currentStep }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, provide, ref, watch } from 'vue'
import { t, setLang } from '../i18n'
import { useThemeStore } from '../stores/themeStore'
import OobeStepWelcome from './OobeStepWelcome.vue'
import OobeStepTheme from './OobeStepTheme.vue'
import OobeStepModel from './OobeStepModel.vue'
import OobeStepPerformance from './OobeStepPerformance.vue'
import OobeStepReady from './OobeStepReady.vue'
import OobeStepTutorial from './OobeStepTutorial.vue'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['complete'])

const themeStore = useThemeStore()
const currentStep = ref(1)
const direction = ref('next')
const isExiting = ref(false)
const totalSteps = 6
const stepRef = ref(null)

const oobeData = reactive({
  lang: 'en',
  themeStyle: 'desk',
  themeMode: 'dark',
  models: {
    ultra: { id: 'rapidocr-mobile-cn', installed: true, active: true },
    standard: { id: 'cnocr-standard-cn', installed: false, active: false, downloading: false, progress: 0, skipped: false },
    pro: { id: 'onnxtr-standard', installed: false, active: false, downloading: false, progress: 0, skipped: false }
  },
  performance: 'balanced',
  tutorialCompleted: false
})

provide('oobeData', oobeData)

watch(() => oobeData.lang, (lang) => {
  setLang(lang)
})

const stepComponents = {
  1: OobeStepWelcome,
  2: OobeStepTheme,
  3: OobeStepModel,
  4: OobeStepPerformance,
  5: OobeStepReady,
  6: OobeStepTutorial
}

const currentComponent = computed(() => stepComponents[currentStep.value])
const transitionName = computed(() => direction.value === 'next' ? 'oobe-next' : 'oobe-prev')

const tutorialButtonText = computed(() => {
  const tip = stepRef.value?.currentTip ?? 1
  return tip >= 4 ? t('oobe_tutorial_finish') : t('oobe_tutorial_next')
})

function nextStep() {
  if (currentStep.value >= 4) return
  direction.value = 'next'
  currentStep.value++
}

function prevStep() {
  if (currentStep.value <= 1) return
  direction.value = 'prev'
  currentStep.value--
}

function enterTutorial() {
  direction.value = 'next'
  currentStep.value = 6
}

function tutorialNext() {
  const tip = stepRef.value?.currentTip ?? 1
  if (tip >= 4) {
    oobeData.tutorialCompleted = true
    finishOobe()
  } else {
    stepRef.value?.nextTip()
  }
}

function skipTutorial() {
  oobeData.tutorialCompleted = false
  finishOobe()
}

function finishOobe() {
  isExiting.value = true
  setTimeout(() => {
    emit('complete', { ...oobeData })
  }, 500)
}

provide('oobeNext', nextStep)
provide('oobePrev', prevStep)
provide('oobeFinish', finishOobe)
</script>

<style scoped>
.oobe-shell {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--v-bg);
  display: grid;
  grid-template-rows: 1fr auto;
  place-items: center;
  padding: var(--s8);
  overflow: hidden;
  transition: opacity 400ms var(--ease-cut);
}

.oobe-shell.is-exiting {
  opacity: 0;
  pointer-events: none;
}

.oobe-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, var(--v-accent-08) 1px, transparent 1px),
    linear-gradient(to bottom, var(--v-accent-08) 1px, transparent 1px);
  background-size: 80px 80px;
  opacity: 0.3;
  pointer-events: none;
}

.oobe-card {
  width: 100%;
  max-width: 720px;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding: var(--s10) var(--s8);
  position: relative;
  overflow: hidden;
}

.oobe-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--v-accent);
  transform: scaleX(0);
  transform-origin: left;
  animation: oobe-line-in var(--dur-base) var(--ease-cut) forwards;
}

@keyframes oobe-line-in {
  to { transform: scaleX(1); }
}

.oobe-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--s8);
  padding-top: var(--s6);
  border-top: 1px solid var(--v-border);
}

.oobe-btn-ghost {
  height: 36px;
  padding-inline: var(--s4);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--r3);
  color: var(--v-text-muted);
  font-family: var(--font-body);
  font-size: var(--fs-body);
  cursor: pointer;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-btn-ghost:hover {
  color: var(--v-text);
  border-color: var(--v-border);
}

.oobe-btn-primary {
  height: 36px;
  padding-inline: var(--s6);
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

.oobe-btn-primary:hover {
  background: var(--v-accent);
  color: var(--v-coal);
  box-shadow: var(--glow-active);
}

.oobe-ready-actions {
  display: flex;
  justify-content: center;
  margin-top: var(--s8);
  padding-top: var(--s6);
  border-top: 1px solid var(--v-border);
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

.oobe-dots {
  display: flex;
  gap: var(--s3);
  justify-content: center;
  padding: var(--s6);
}

.oobe-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid var(--v-border);
  background: transparent;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-dot.is-active {
  background: var(--v-accent);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.oobe-dot.is-done {
  background: var(--v-accent);
  border-color: var(--v-accent);
  opacity: 0.4;
}

.oobe-next-enter-active,
.oobe-next-leave-active,
.oobe-prev-enter-active,
.oobe-prev-leave-active {
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-next-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.oobe-next-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.oobe-prev-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.oobe-prev-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
