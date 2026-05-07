<template>
  <div style="position: relative;">
    <button class="v-state-tab" type="button" style="height: 32px;" @click="open = !open">
      {{ currentLang === 'zh' ? '中文' : 'EN' }}
    </button>
    <div
      v-if="open"
      class="v-panel-rail"
      style="position: absolute; right: 0; top: calc(100% + var(--s2)); z-index: 20; width: 132px; padding: var(--s2);"
    >
      <button
        v-for="item in langs"
        :key="item.key"
        type="button"
        class="v-state-tab"
        :class="{ 'is-active': currentLang === item.key }"
        style="width: 100%; margin-bottom: var(--s1);"
        @click="choose(item.key)"
      >
        {{ item.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { currentLang, setLang } from '../i18n'

const open = ref(false)
const langs = [
  { key: 'zh', label: '中文' },
  { key: 'en', label: 'ENGLISH' },
]

function choose(lang) {
  setLang(lang)
  open.value = false
}
</script>
