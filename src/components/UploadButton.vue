<template>
  <div
    ref="buttonRef"
    class="upload-button-wrapper"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <VButton
      :type="isWide ? 'secondary' : 'icon'"
      :size="isWide ? 'lg' : undefined"
      :class="['upload-button', { wide: isWide, narrow: !isWide }]"
      :block="isWide"
      @click="fileInput.click()"
    >
      <template #icon>
        <svg
          v-if="isWide"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M8 2V10M8 10L5 7M8 10L11 7M2 11V12.5C2 13.3284 2.67157 14 3.5 14H12.5C13.3284 14 14 13.3284 14 12.5V11"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <svg
          v-else
          width="20"
          height="20"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M8 2V10M8 10L5 7M8 10L11 7M2 11V12.5C2 13.3284 2.67157 14 3.5 14H12.5C13.3284 14 14 13.3284 14 12.5V11"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </template>
      <template v-if="isWide">
        <span class="upload-label">上传</span>
      </template>
    </VButton>

    <!-- Tooltip -->
    <Transition name="tooltip">
      <div v-if="showTooltip && !isWide" class="upload-tooltip">
        上传文件
      </div>
    </Transition>

    <input
      ref="fileInput"
      type="file"
      multiple
      accept="image/*,.pdf"
      hidden
      @change="onFileSelect"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import VButton from './VButton.vue'
import { useFileUpload } from '../composables/useFileUpload'

const BREAKPOINT = 768

const fileInput = ref(null)
const buttonRef = ref(null)
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)
const showTooltip = ref(false)
let tooltipTimer = null
let resizeTimer = null

const isWide = computed(() => windowWidth.value > BREAKPOINT)

const { addFiles } = useFileUpload()

function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    windowWidth.value = window.innerWidth
  }, 150)
}

function onMouseEnter() {
  if (isWide.value) return
  tooltipTimer = setTimeout(() => {
    showTooltip.value = true
  }, 300)
}

function onMouseLeave() {
  clearTimeout(tooltipTimer)
  showTooltip.value = false
}

function onFileSelect(e) {
  const files = e.target.files
  if (files?.length) {
    addFiles(files)
  }
  e.target.value = ''
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(tooltipTimer)
  clearTimeout(resizeTimer)
})
</script>

<style scoped>
.upload-button-wrapper {
  position: relative;
  display: inline-flex;
}

.upload-button {
  transition:
    width 0.3s ease,
    height 0.3s ease,
    background-color 0.15s var(--ease-cut),
    border-color 0.15s var(--ease-cut),
    box-shadow 0.15s var(--ease-cut);
  overflow: hidden;
}

.upload-button.wide {
  width: 100%;
  height: 40px;
}

.upload-button.narrow {
  width: 40px;
  height: 40px;
  padding: 0;
}

.upload-label {
  transition: opacity 0.15s ease;
}

.upload-tooltip {
  position: absolute;
  top: 50%;
  left: calc(100% + 8px);
  transform: translateY(-50%);
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  padding: var(--s1) var(--s2);
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--v-text);
  white-space: nowrap;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.15s ease;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .upload-button {
    transition: none;
  }
  .upload-label {
    transition: none;
  }
  .tooltip-enter-active,
  .tooltip-leave-active {
    transition: none;
  }
}
</style>
