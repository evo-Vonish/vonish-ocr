<template>
  <div class="oobe-step">
    <h1 class="oobe-step-title">{{ t('oobe_theme_title') }}</h1>
    <p class="oobe-step-subtitle">{{ t('oobe_theme_subtitle') }}</p>

    <!-- 风格三选一 -->
    <div class="oobe-style-grid">
      <div
        v-for="s in styles"
        :key="s.key"
        class="v-card oobe-style-card"
        :class="{ 'is-active': oobeData.themeStyle === s.key }"
        @click="selectStyle(s.key)"
      >
        <div class="oobe-style-name">{{ s.label }}</div>
        <div class="oobe-style-desc">{{ s.desc }}</div>
      </div>
    </div>

    <!-- 模式二选一 -->
    <div class="oobe-mode-label">DISPLAY MODE</div>
    <div class="oobe-mode-grid">
      <div
        v-for="m in modes"
        :key="m.key"
        class="v-card oobe-mode-card"
        :class="{ 'is-active': oobeData.themeMode === m.key }"
        @click="selectMode(m.key)"
      >
        {{ m.label }}
      </div>
    </div>

    <!-- 实时预览 -->
    <div class="oobe-preview-label">{{ t('oobe_preview') }}</div>
    <MiniDeskPreview :style="oobeData.themeStyle" :mode="oobeData.themeMode" />
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { t } from '../i18n'
import MiniDeskPreview from './MiniDeskPreview.vue'

const oobeData = inject('oobeData')

const styles = computed(() => [
  { key: 'desk', label: t('oobe_style_desk'), desc: t('oobe_style_desk_desc') },
  { key: 'mono', label: t('oobe_style_mono'), desc: t('oobe_style_mono_desc') },
  { key: 'hc', label: t('oobe_style_hc'), desc: t('oobe_style_hc_desc') }
])

const modes = computed(() => [
  { key: 'dark', label: t('oobe_mode_dark') },
  { key: 'light', label: t('oobe_mode_light') }
])

function selectStyle(style) {
  oobeData.themeStyle = style
}

function selectMode(mode) {
  oobeData.themeMode = mode
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

.oobe-style-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s3);
  margin-bottom: var(--s6);
}

.oobe-style-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s1);
  padding: var(--s4);
  min-height: 80px;
  cursor: pointer;
  text-align: center;
}

.oobe-style-name {
  font-family: var(--font-body);
  font-size: var(--fs-small);
  font-weight: var(--fw-semibold);
  color: var(--v-text);
}

.oobe-style-desc {
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.oobe-mode-label {
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  letter-spacing: 0.06em;
  margin-bottom: var(--s3);
  text-transform: uppercase;
}

.oobe-mode-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s3);
  margin-bottom: var(--s6);
}

.oobe-mode-card {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--s3);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: var(--fs-small);
  font-weight: var(--fw-semibold);
  color: var(--v-text);
  min-height: 44px;
}

.oobe-preview-label {
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  letter-spacing: 0.06em;
  margin-bottom: var(--s3);
  text-transform: uppercase;
}
</style>
