import { ref } from 'vue'
import zh from './zh.json'
import en from './en.json'

const STORAGE_KEY = 'vonishocr-lang'
const dictionaries = { zh, en }

export const currentLang = ref('zh')

export function t(key) {
  return dictionaries[currentLang.value]?.[key] || dictionaries.zh[key] || key
}

export function setLang(lang) {
  const next = lang === 'en' ? 'en' : 'zh'
  currentLang.value = next
  window.localStorage.setItem(STORAGE_KEY, next)
  document.documentElement.lang = next === 'zh' ? 'zh-CN' : 'en'
}

export function initLang() {
  const saved = window.localStorage.getItem(STORAGE_KEY)
  const system = navigator.language.startsWith('zh') ? 'zh' : 'en'
  setLang(saved || system)
}
