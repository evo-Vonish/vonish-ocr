<template>
  <section class="theme-control">
    <h4>{{ t('config_theme_style') }}</h4>
    <div class="capsule-grid style-grid" role="radiogroup" :aria-label="t('config_theme_style')">
      <button
        v-for="item in styles"
        :key="item.key"
        type="button"
        class="theme-capsule"
        :class="{ active: themeStore.resolvedStyle === item.key }"
        @click="themeStore.setThemeStyle(item.key)"
      >
        <span class="capsule-dot"></span>
        <span>{{ t(item.labelKey) }}</span>
      </button>
    </div>

    <h4>{{ t('config_theme_mode') }}</h4>
    <div class="capsule-grid mode-grid" role="radiogroup" :aria-label="t('config_theme_mode')">
      <button
        v-for="item in modes"
        :key="item.key"
        type="button"
        class="theme-capsule"
        :class="{ active: themeStore.resolvedMode === item.key }"
        @click="themeStore.setThemeMode(item.key)"
      >
        <span class="capsule-dot"></span>
        <span>{{ t(item.labelKey) }}</span>
      </button>
    </div>

    <label class="follow-row">
      <input type="checkbox" :checked="themeStore.followSystem" @change="themeStore.setFollowSystem($event.target.checked)" />
      <span>{{ t('config_follow_system') }}</span>
      <span class="follow-meta">{{ systemLabel }}</span>
    </label>

    <div class="theme-preview">
      <div class="preview-swatches">
        <span class="swatch bg"></span>
        <span class="swatch text"></span>
        <span class="swatch accent"></span>
      </div>
      <div>
        <div class="preview-title">{{ resolvedLabel }}</div>
        <div class="preview-copy">{{ previewCopy }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useThemeStore } from '../stores/themeStore'
import { t } from '../i18n'

const themeStore = useThemeStore()

const styles = [
  { key: 'desk', labelKey: 'theme_style_desk' },
  { key: 'mono', labelKey: 'theme_style_mono' },
  { key: 'hc', labelKey: 'theme_style_hc' },
]

const modes = [
  { key: 'dark', labelKey: 'theme_mode_dark' },
  { key: 'light', labelKey: 'theme_mode_light' },
]

const names = {
  desk: '证据桌',
  mono: '黑白审阅',
  hc: '高对比',
  dark: '深色',
  light: '浅色',
}

const resolvedLabel = computed(() => `${names[themeStore.resolvedStyle]} · ${names[themeStore.resolvedMode]}`)
const systemLabel = computed(() => `${names[themeStore.detectedStyle]} / ${names[themeStore.detectedMode]}`)
const previewCopy = computed(() => {
  if (themeStore.resolvedStyle === 'desk') return '掌灯青 / 纸骨 / 炭黑'
  if (themeStore.resolvedStyle === 'mono') return '白 / 黑 / 灰'
  return '强边界 / 强焦点 / 强可见'
})
</script>

<style scoped>
.theme-control {
  display: grid;
  gap: var(--s3);
}

.theme-control h4 {
  margin: 0;
}

.capsule-grid {
  display: grid;
  gap: var(--s2);
}

.style-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.mode-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.theme-capsule {
  min-height: 42px;
  display: grid;
  place-items: center;
  gap: 2px;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  cursor: pointer;
}

.theme-capsule.active {
  border: 2px solid var(--v-accent);
  color: var(--v-text);
  box-shadow: var(--glow-soft);
}

.capsule-dot {
  width: 7px;
  height: 7px;
  border: 1px solid currentColor;
  border-radius: 50%;
}

.theme-capsule.active .capsule-dot {
  background: var(--v-accent);
  border-color: var(--v-accent);
}

.follow-row {
  display: flex;
  align-items: center;
  gap: var(--s2);
  color: var(--v-text-muted);
}

.follow-meta {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
}

.theme-preview {
  min-height: 70px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: var(--s3);
  padding: var(--s3);
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.preview-swatches {
  display: flex;
  gap: 5px;
}

.swatch {
  width: 22px;
  height: 42px;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
}

.swatch.bg { background: var(--v-bg); }
.swatch.text { background: var(--v-text); }
.swatch.accent { background: var(--v-accent); }

.preview-title {
  font-weight: var(--fw-semibold);
  color: var(--v-text);
}

.preview-copy {
  margin-top: var(--s1);
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
}
</style>
