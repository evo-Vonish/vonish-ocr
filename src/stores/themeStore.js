import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_KEY = 'vonish-ocr:appearance:v4'
const LEGACY_KEY = 'vonish-ocr:theme:v2'

function systemMode() {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function systemHighContrast() {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(forced-colors: active)').matches || window.matchMedia('(prefers-contrast: more)').matches
}

function normalizeAppearance(value) {
  if (value === 'desk') return 'evidence'
  if (value === 'mono') return 'professional'
  return ['evidence', 'professional'].includes(value) ? value : 'evidence'
}

function normalizeMode(value) {
  return ['dark', 'light'].includes(value) ? value : 'dark'
}

function normalizeHex(value, fallback) {
  const text = String(value || '').trim()
  return /^#[0-9A-Fa-f]{6}$/.test(text) ? text.toUpperCase() : fallback
}

function alphaHex(hex, alpha) {
  const normalized = normalizeHex(hex, '#8FF6D2').replace('#', '')
  const value = Math.round(alpha * 255).toString(16).padStart(2, '0').toUpperCase()
  return `#${normalized}${value}`
}

function legacyToState(raw) {
  try {
    const data = JSON.parse(raw || '{}')
    const style = data.style || data.appearance
    return {
      appearance: normalizeAppearance(style),
      mode: normalizeMode(data.mode),
      followSystem: data.followSystem !== false,
      highContrast: style === 'hc',
    }
  } catch (_) {
    return { appearance: 'evidence', mode: 'dark', followSystem: true, highContrast: false }
  }
}

function applyTheme({ appearance, mode, highContrast, customTokens }) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.classList.add('theme-switching')

  if (highContrast) {
    root.removeAttribute('data-appearance')
    root.removeAttribute('data-theme-mode')
    root.removeAttribute('data-theme-style')
    root.dataset.theme = 'hc'
  } else {
    root.dataset.appearance = appearance
    root.dataset.theme = mode
    root.dataset.themeMode = mode
    root.dataset.themeStyle = appearance
  }

  root.dataset.userTheme = customTokens.enabled ? 'custom' : 'default'
  const accent = normalizeHex(customTokens.accent, '#8FF6D2')
  root.style.setProperty('--user-accent', accent)
  root.style.setProperty('--user-accent-08', alphaHex(accent, 0.08))
  root.style.setProperty('--user-accent-10', alphaHex(accent, 0.10))
  root.style.setProperty('--user-accent-16', alphaHex(accent, 0.16))
  root.style.setProperty('--user-accent-24', alphaHex(accent, 0.24))
  root.style.setProperty('--user-accent-32', alphaHex(accent, 0.32))
  root.style.setProperty('--user-warn', normalizeHex(customTokens.warn, '#D7B95A'))
  root.style.setProperty('--user-error', normalizeHex(customTokens.error, '#B85A50'))
  root.style.setProperty('--user-success', normalizeHex(customTokens.success, '#56F28C'))
  root.style.setProperty('--user-size-offset', `${Number(customTokens.sizeOffset || 0)}px`)
  root.style.setProperty('--user-border-width', `${Number(customTokens.borderWidth || 1)}px`)

  window.setTimeout(() => root.classList.remove('theme-switching'), 160)
}

export const useThemeStore = defineStore('theme', () => {
  const userAppearance = ref('evidence')
  const userMode = ref('dark')
  const followSystem = ref(true)
  const highContrast = ref(false)
  const detectedMode = ref(systemMode())
  const detectedHighContrast = ref(systemHighContrast())
  const customTokens = ref({
    enabled: false,
    accent: '#8FF6D2',
    warn: '#D7B95A',
    error: '#B85A50',
    success: '#56F28C',
    sizeOffset: 0,
    fontWeight: 'normal',
    borderWidth: 1,
    decorationLevel: 1,
  })

  const resolvedAppearance = computed(() => userAppearance.value)
  const resolvedMode = computed(() => followSystem.value ? detectedMode.value : userMode.value)
  const resolvedHighContrast = computed(() => highContrast.value || detectedHighContrast.value)
  const resolvedTheme = computed(() => resolvedHighContrast.value ? 'high-contrast' : `${resolvedAppearance.value}-${resolvedMode.value}`)

  // Backward-compatible names used by existing components.
  const userStyle = computed({
    get: () => userAppearance.value,
    set: (value) => { userAppearance.value = normalizeAppearance(value) },
  })
  const resolvedStyle = computed(() => resolvedHighContrast.value ? 'hc' : resolvedAppearance.value)
  const userTheme = computed(() => followSystem.value ? 'system' : resolvedTheme.value)
  const detectedStyle = computed(() => detectedHighContrast.value ? 'hc' : userAppearance.value)

  function persist() {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      appearance: userAppearance.value,
      mode: userMode.value,
      followSystem: followSystem.value,
      highContrast: highContrast.value,
      customTokens: customTokens.value,
    }))
  }

  function refreshDom() {
    applyTheme({
      appearance: resolvedAppearance.value,
      mode: resolvedMode.value,
      highContrast: resolvedHighContrast.value,
      customTokens: customTokens.value,
    })
  }

  function loadTheme() {
    if (typeof window !== 'undefined') {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (raw) {
        try {
          const data = JSON.parse(raw)
          userAppearance.value = normalizeAppearance(data.appearance)
          userMode.value = normalizeMode(data.mode)
          followSystem.value = data.followSystem !== false
          highContrast.value = !!data.highContrast
          customTokens.value = { ...customTokens.value, ...(data.customTokens || {}) }
        } catch (_) {
          window.localStorage.removeItem(STORAGE_KEY)
        }
      } else {
        const migrated = legacyToState(window.localStorage.getItem(LEGACY_KEY))
        userAppearance.value = migrated.appearance
        userMode.value = migrated.mode
        followSystem.value = migrated.followSystem
        highContrast.value = migrated.highContrast
        persist()
      }
      detectedMode.value = systemMode()
      detectedHighContrast.value = systemHighContrast()
    }
    refreshDom()
  }

  function setAppearance(appearance) {
    userAppearance.value = normalizeAppearance(appearance)
    highContrast.value = false
    persist()
    refreshDom()
  }

  function setThemeStyle(style) {
    if (style === 'hc') {
      setHighContrast(true)
      return
    }
    setAppearance(style)
  }

  function setThemeMode(mode) {
    userMode.value = normalizeMode(mode)
    followSystem.value = false
    persist()
    refreshDom()
  }

  function setFollowSystem(value) {
    followSystem.value = !!value
    persist()
    refreshDom()
  }

  function setHighContrast(value) {
    highContrast.value = !!value
    persist()
    refreshDom()
  }

  function setTheme(value) {
    if (value === 'system') {
      setFollowSystem(true)
      return
    }
    if (value === 'hc' || value === 'high-contrast') {
      setHighContrast(true)
      return
    }
    const [appearance, mode] = String(value || '').split('-')
    userAppearance.value = normalizeAppearance(appearance)
    userMode.value = normalizeMode(mode)
    highContrast.value = false
    followSystem.value = false
    persist()
    refreshDom()
  }

  function setCustomToken(key, value) {
    const next = { ...customTokens.value }
    if (['accent', 'warn', 'error', 'success'].includes(key)) {
      next[key] = normalizeHex(value, next[key])
    } else if (['sizeOffset', 'borderWidth', 'decorationLevel'].includes(key)) {
      next[key] = Number(value)
    } else if (key === 'enabled') {
      next.enabled = !!value
    } else if (key === 'fontWeight') {
      next.fontWeight = String(value || 'normal')
    }
    customTokens.value = next
    persist()
    refreshDom()
  }

  function resetCustomTokens() {
    customTokens.value = {
      enabled: false,
      accent: '#8FF6D2',
      warn: '#D7B95A',
      error: '#B85A50',
      success: '#56F28C',
      sizeOffset: 0,
      fontWeight: 'normal',
      borderWidth: 1,
      decorationLevel: 1,
    }
    persist()
    refreshDom()
  }

  function watchSystemTheme() {
    if (typeof window === 'undefined') return
    const update = () => {
      detectedMode.value = systemMode()
      detectedHighContrast.value = systemHighContrast()
      if (followSystem.value || detectedHighContrast.value) refreshDom()
    }
    window.matchMedia('(forced-colors: active)').addEventListener('change', update)
    window.matchMedia('(prefers-contrast: more)').addEventListener('change', update)
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', update)
    window.addEventListener('focus', update)
  }

  return {
    userAppearance,
    userStyle,
    userMode,
    userTheme,
    followSystem,
    highContrast,
    detectedStyle,
    detectedMode,
    detectedHighContrast,
    resolvedAppearance,
    resolvedStyle,
    resolvedMode,
    resolvedHighContrast,
    resolvedTheme,
    customTokens,
    loadTheme,
    setTheme,
    setAppearance,
    setThemeStyle,
    setThemeMode,
    setFollowSystem,
    setHighContrast,
    setCustomToken,
    resetCustomTokens,
    watchSystemTheme,
  }
})
