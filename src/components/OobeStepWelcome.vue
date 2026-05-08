<template>
  <div class="oobe-step">
    <h1 class="oobe-step-title">{{ t('oobe_welcome_title') }}</h1>
    <p class="oobe-step-subtitle">{{ t('oobe_welcome_subtitle') }}</p>

    <div class="oobe-lang-label">{{ t('oobe_select_language') }}</div>
    <div class="oobe-lang-grid">
      <div
        class="v-card oobe-lang-card"
        :class="{ 'is-active': oobeData.lang === 'en' }"
        @click="selectLang('en')"
      >
        <span class="oobe-lang-dot" :class="{ 'is-active': oobeData.lang === 'en' }"></span>
        <span class="oobe-lang-code">EN</span>
        <span class="oobe-lang-name">English</span>
      </div>
      <div
        class="v-card oobe-lang-card"
        :class="{ 'is-active': oobeData.lang === 'zh' }"
        @click="selectLang('zh')"
      >
        <span class="oobe-lang-dot" :class="{ 'is-active': oobeData.lang === 'zh' }"></span>
        <span class="oobe-lang-code">??</span>
        <span class="oobe-lang-name">{{ t('language_zh') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { t } from '../i18n'

const oobeData = inject('oobeData')

function selectLang(lang) {
  oobeData.lang = lang
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
  margin-bottom: var(--s8);
}

.oobe-lang-label {
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  letter-spacing: 0.06em;
  margin-bottom: var(--s4);
  text-transform: uppercase;
}

.oobe-lang-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s4);
}

.oobe-lang-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s2);
  padding: var(--s6);
  cursor: pointer;
  min-height: 120px;
}

.oobe-lang-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid var(--v-border);
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-lang-dot.is-active {
  background: var(--v-accent);
  border-color: var(--v-accent);
}

.oobe-lang-code {
  font-family: var(--font-body);
  font-size: 18px;
  font-weight: var(--fw-semibold);
  color: var(--v-text);
}

.oobe-lang-name {
  font-family: var(--font-body);
  font-size: var(--fs-small);
  color: var(--v-text-muted);
}
</style>
