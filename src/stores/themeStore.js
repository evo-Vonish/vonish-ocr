import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_KEY = 'vonish-ocr:theme:v2'
const LEGACY_KEY = 'vonish-ocr:theme:v1'

function systemMode() {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function systemStyle() {
  if (typeof window === 'undefined') return 'desk'
  const forcedColors = window.matchMedia('(forced-colors: active)').matches
  const prefersContrast = window.matchMedia('(prefers-contrast: more)').matches
  return forcedColors || prefersContrast ? 'hc' : 'desk'
}

function normalizeStyle(value) {
  return ['desk', 'mono', 'hc'].includes(value) ? value : 'desk'
}

function normalizeMode(value) {
  return ['dark', 'light'].includes(value) ? value : 'dark'
}

function legacyToState(value) {
  if (value === 'light') return { style: 'desk', mode: 'light', followSystem: false }
  if (value === 'mono') return { style: 'mono', mode: 'dark', followSystem: false }
  if (value === 'hc') return { style: 'hc', mode: 'dark', followSystem: false }
  return { style: 'desk', mode: 'dark', followSystem: !value }
}

function applyTheme(style, mode) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.classList.add('theme-switching')
  root.dataset.themeStyle = style
  root.dataset.themeMode = mode
  root.dataset.theme = `${style}-${mode}`
  window.setTimeout(() => root.classList.remove('theme-switching'), 160)
}

export const useThemeStore = defineStore('theme', () => {
  const userStyle = ref('desk')
  const userMode = ref('dark')
  const followSystem = ref(true)
  const detectedStyle = ref(systemStyle())
  const detectedMode = ref(systemMode())

  const resolvedStyle = computed(() => followSystem.value ? detectedStyle.value : userStyle.value)
  const resolvedMode = computed(() => followSystem.value ? detectedMode.value : userMode.value)
  const resolvedTheme = computed(() => `${resolvedStyle.value}-${resolvedMode.value}`)
  const userTheme = computed(() => followSystem.value ? 'system' : resolvedTheme.value)

  function persist() {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      style: userStyle.value,
      mode: userMode.value,
      followSystem: followSystem.value,
    }))
  }

  function loadTheme() {
    if (typeof window !== 'undefined') {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (raw) {
        try {
          const data = JSON.parse(raw)
          userStyle.value = normalizeStyle(data.style)
          userMode.value = normalizeMode(data.mode)
          followSystem.value = data.followSystem !== false
        } catch (_) {
          window.localStorage.removeItem(STORAGE_KEY)
        }
      } else {
        const legacy = window.localStorage.getItem(LEGACY_KEY)
        const migrated = legacyToState(legacy)
        userStyle.value = migrated.style
        userMode.value = migrated.mode
        followSystem.value = migrated.followSystem
        persist()
      }
      detectedStyle.value = systemStyle()
      detectedMode.value = systemMode()
    }
    applyTheme(resolvedStyle.value, resolvedMode.value)
  }

  function setThemeStyle(style) {
    userStyle.value = normalizeStyle(style)
    followSystem.value = false
    persist()
    applyTheme(resolvedStyle.value, resolvedMode.value)
  }

  function setThemeMode(mode) {
    userMode.value = normalizeMode(mode)
    followSystem.value = false
    persist()
    applyTheme(resolvedStyle.value, resolvedMode.value)
  }

  function setFollowSystem(value) {
    followSystem.value = !!value
    persist()
    applyTheme(resolvedStyle.value, resolvedMode.value)
  }

  function setTheme(value) {
    if (value === 'system') {
      setFollowSystem(true)
      return
    }
    const [style, mode] = String(value || '').split('-')
    userStyle.value = normalizeStyle(style === 'dark' || style === 'light' ? 'desk' : style)
    userMode.value = normalizeMode(mode || (value === 'light' ? 'light' : 'dark'))
    followSystem.value = false
    persist()
    applyTheme(resolvedStyle.value, resolvedMode.value)
  }

  function watchSystemTheme() {
    if (typeof window === 'undefined') return
    const update = () => {
      detectedStyle.value = systemStyle()
      detectedMode.value = systemMode()
      if (followSystem.value) applyTheme(resolvedStyle.value, resolvedMode.value)
    }
    window.matchMedia('(forced-colors: active)').addEventListener('change', update)
    window.matchMedia('(prefers-contrast: more)').addEventListener('change', update)
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', update)
  }

  return {
    userStyle,
    userMode,
    userTheme,
    followSystem,
    detectedStyle,
    detectedMode,
    resolvedStyle,
    resolvedMode,
    resolvedTheme,
    loadTheme,
    setTheme,
    setThemeStyle,
    setThemeMode,
    setFollowSystem,
    watchSystemTheme,
  }
})
