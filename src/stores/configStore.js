import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getConfig,
  saveConfig,
  getAvailableModels,
  pullModel,
  openModelDir,
  parseApiError,
  getAISchemes,
  saveAIScheme,
  setActiveAIScheme,
} from '../api/tauri_ipc'

export const useConfigStore = defineStore('config', () => {
  // State
  const config = ref({
    ocr_model: 'auto',
    preprocess: true,
    auto_rotate: true,
    perspective_correct: false,
    scene_detect: true,
    ai: {
      enabled: false,
      provider: 'deepseek',
      api_key: '',
      api_base: '',
      model: '',
      temperature: 0.3,
      trigger_mode: 'auto',
    },
    output_mode: 'smart',
    include_diff: false,
    power_mode: 'balanced',
    preload_model: true,
    notify_enabled: true,
  })

  const models = ref({ available: [], local: [] })
  const aiSchemes = ref([])
  const activeAiSchemeId = ref(null)
  const isLoading = ref(false)
  const pullProgress = ref(null)

  // Actions
  async function loadConfig() {
    try {
      const data = await getConfig()
      if (data) {
        config.value = { ...config.value, ...data }
      }
    } catch (e) {
      console.error('加载配置失败:', e)
    }
  }

  async function updateConfig(newConfig) {
    config.value = { ...config.value, ...newConfig }
    try {
      await saveConfig(config.value)
    } catch (e) {
      console.error('保存配置失败:', e)
      throw e
    }
  }

  async function loadModels() {
    try {
      models.value = await getAvailableModels()
    } catch (e) {
      console.error('加载模型列表失败:', e)
    }
  }

  async function loadAISchemes() {
    try {
      const data = await getAISchemes()
      aiSchemes.value = data.schemes || []
      activeAiSchemeId.value = data.active_scheme_id || null
    } catch (e) {
      console.error('加载 AI 方案失败:', e)
    }
  }

  async function upsertAIScheme(scheme) {
    const data = await saveAIScheme(scheme)
    await loadAISchemes()
    return data.scheme
  }

  async function activateAIScheme(schemeId) {
    await setActiveAIScheme(schemeId)
    activeAiSchemeId.value = schemeId
    aiSchemes.value = aiSchemes.value.map(s => ({ ...s }))
  }

  async function downloadModel(modelId) {
    isLoading.value = true
    pullProgress.value = { modelId, progress: 0, status: 'downloading' }
    try {
      const result = await pullModel(modelId)
      pullProgress.value = { modelId, progress: 100, status: 'completed' }
      await loadModels() // 刷新本地模型列表
      return result
    } catch (e) {
      const parsed = parseApiError(e, '模型下载失败')
      pullProgress.value = { modelId, progress: 0, status: 'failed', error: parsed.message }
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function openModelsFolder() {
    try {
      await openModelDir()
    } catch (e) {
      console.error('打开模型目录失败:', e)
    }
  }

  return {
    config,
    models,
    aiSchemes,
    activeAiSchemeId,
    isLoading,
    pullProgress,
    loadConfig,
    updateConfig,
    loadModels,
    loadAISchemes,
    upsertAIScheme,
    activateAIScheme,
    downloadModel,
    openModelsFolder,
  }
})
