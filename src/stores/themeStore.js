import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_KEY = 'vonish-ocr:theme:v1'

function getSystemTheme() {
  if (typeof window === 'undefined') return 'dark'
  const forcedColors = window.matchMedia('(forced-colors: active)').matches
  const prefersContrast = window.matchMedia('(prefers-contrast: more)').matches
  if (forcedColors || prefersContrast) return 'hc'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function applyTheme(theme) {
  if (typeof document === 'undefined') return
  document.documentElement.dataset.theme = theme
}

export const useThemeStore = defineStore('theme', () => {
  const userTheme = ref(null)
  const systemTheme = ref(getSystemTheme())

  const resolvedTheme = computed(() => userTheme.value || systemTheme.value)

  function loadTheme() {
    if (typeof window !== 'undefined') {
      userTheme.value = window.localStorage.getItem(STORAGE_KEY) || null
      systemTheme.value = getSystemTheme()
    }
    applyTheme(resolvedTheme.value)
  }

  function setTheme(theme) {
    userTheme.value = theme === 'system' ? null : theme
    if (typeof window !== 'undefined') {
      if (userTheme.value) {
        window.localStorage.setItem(STORAGE_KEY, userTheme.value)
      } else {
        window.localStorage.removeItem(STORAGE_KEY)
      }
    }
    applyTheme(resolvedTheme.value)
  }

  function watchSystemTheme() {
    if (typeof window === 'undefined') return
    const update = () => {
      systemTheme.value = getSystemTheme()
      if (!userTheme.value) applyTheme(systemTheme.value)
    }
    window.matchMedia('(forced-colors: active)').addEventListener('change', update)
    window.matchMedia('(prefers-contrast: more)').addEventListener('change', update)
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', update)
  }

  return {
    userTheme,
    systemTheme,
    resolvedTheme,
    loadTheme,
    setTheme,
    watchSystemTheme,
  }
})
