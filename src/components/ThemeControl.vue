<template>
  <section class="theme-control">
    <h4>{{ t('config_theme_style') }}</h4>
    <div class="capsule-grid style-grid" role="radiogroup" :aria-label="t('config_theme_style')">
      <button
        v-for="item in appearances"
        :key="item.key"
        type="button"
        class="theme-capsule"
        :class="{ active: themeStore.resolvedAppearance === item.key && !themeStore.resolvedHighContrast }"
        @click="themeStore.setAppearance(item.key)"
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
        :class="{ active: themeStore.resolvedMode === item.key && !themeStore.resolvedHighContrast }"
        @click="themeStore.setThemeMode(item.key)"
      >
        <span class="capsule-dot"></span>
        <span>{{ t(item.labelKey) }}</span>
      </button>
    </div>

    <label class="toggle-row">
      <input type="checkbox" :checked="themeStore.followSystem" @change="themeStore.setFollowSystem($event.target.checked)" />
      <span>{{ t('config_follow_system') }}</span>
      <span class="follow-meta">{{ systemLabel }}</span>
    </label>

    <label class="toggle-row">
      <input type="checkbox" :checked="themeStore.highContrast" @change="themeStore.setHighContrast($event.target.checked)" />
      <span>{{ t('theme_high_contrast') }}</span>
      <span class="follow-meta">{{ themeStore.resolvedHighContrast ? 'ON' : 'OFF' }}</span>
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

    <button class="lab-entry" type="button" @click="labVisible = true">
      <span>
        <strong>{{ t('theme_appearance_lab') }}</strong>
        <small>{{ labSummary }}</small>
      </span>
      <span class="lab-open">OPEN</span>
    </button>

    <AppearanceLabModal v-model:visible="labVisible" />
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useThemeStore } from '../stores/themeStore'
import { currentLang, t } from '../i18n'
import AppearanceLabModal from './AppearanceLabModal.vue'

const themeStore = useThemeStore()
const labVisible = ref(false)

const appearances = [
  { key: 'evidence', labelKey: 'theme_style_evidence' },
  { key: 'professional', labelKey: 'theme_style_professional' },
]

const modes = [
  { key: 'dark', labelKey: 'theme_mode_dark' },
  { key: 'light', labelKey: 'theme_mode_light' },
]

const names = computed(() => ({
  evidence: t('theme_style_evidence'),
  professional: t('theme_style_professional'),
  hc: t('theme_style_hc'),
  dark: t('theme_mode_dark'),
  light: t('theme_mode_light'),
}))

const resolvedLabel = computed(() => {
  if (themeStore.resolvedHighContrast) return t('theme_style_hc')
  return `${names.value[themeStore.resolvedAppearance]} / ${names.value[themeStore.resolvedMode]}`
})

const systemLabel = computed(() => themeStore.detectedHighContrast ? 'HC' : names.value[themeStore.detectedMode])

const previewCopy = computed(() => {
  if (themeStore.resolvedHighContrast) return t('theme_preview_hc')
  if (themeStore.resolvedAppearance === 'professional') return t('theme_preview_professional')
  return t('theme_preview_evidence')
})

const labSummary = computed(() => currentLang.value === 'zh'
  ? '颜色令牌、强调色和安全预览'
  : 'Color tokens, accent and safe preview'
)
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

.style-grid,
.mode-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.theme-capsule {
  min-height: 42px;
  display: grid;
  place-items: center;
  gap: 2px;
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  cursor: pointer;
  transition: var(--theme-transition);
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

.toggle-row {
  display: flex;
  align-items: center;
  gap: var(--s2);
  color: var(--v-text-muted);
}

.toggle-row input {
  accent-color: var(--v-accent);
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
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
}

.preview-swatches {
  display: flex;
  gap: var(--s1);
}

.swatch {
  width: 22px;
  height: 42px;
  border: var(--v-border-width) solid var(--v-border);
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

.lab-entry {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  padding: var(--s3);
  background: var(--v-panel);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text);
  text-align: left;
  cursor: pointer;
}

.lab-entry strong,
.lab-entry small {
  display: block;
}

.lab-entry small {
  margin-top: var(--s1);
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
}

.lab-entry:hover {
  border-color: var(--v-accent);
}

.lab-open {
  font-family: var(--font-mono);
  color: var(--v-accent);
  font-size: var(--fs-caption);
}
</style>
