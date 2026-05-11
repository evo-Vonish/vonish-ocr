<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="visible" class="drawer-overlay" @click.self="close">
        <aside class="drawer">
          <header class="drawer-header">
            <div>
              <div class="drawer-kicker">{{ t('config_local_settings') }}</div>
              <h3 class="drawer-title v-title">{{ t('config_title') }}</h3>
            </div>
            <button class="close-btn" type="button" :title="t('btn_close')" @click="close">
              <span aria-hidden="true"></span>
            </button>
          </header>

          <div class="drawer-body">
            <section>
              <ThemeControl />
            </section>

            <section>
              <h4>{{ t('config_language') }}</h4>
              <div class="v-state-tabs">
                <button class="v-state-tab" type="button" :class="{ 'is-active': currentLang === 'zh' }" @click="setLang('zh')">{{ t('config_lang_zh') }}</button>
                <button class="v-state-tab" type="button" :class="{ 'is-active': currentLang === 'en' }" @click="setLang('en')">{{ t('config_lang_en') }}</button>
              </div>
            </section>

            <section>
              <h4>{{ t('config_ocr_model') }}</h4>
              <select v-model="config.ocr_model">
                <option value="rapidocr-mobile-cn">{{ t('config_model_ultra') }}</option>
                <option value="cnocr-standard-cn">{{ t('config_model_standard') }}</option>
              </select>
              <button class="wide-action" type="button" @click="emit('open-langpacks')">{{ t('config_open_langpacks') }}</button>
              <p class="hint-text">{{ t('config_langpack_hint') }}</p>
            </section>

            <section>
              <h4>{{ t('config_preprocess') }}</h4>
              <label><input type="checkbox" v-model="config.preprocess" /> {{ t('config_enable_preprocess') }}</label>
              <label><input type="checkbox" v-model="config.auto_rotate" /> {{ t('config_auto_rotate') }}</label>
              <label><input type="checkbox" v-model="config.perspective_correct" /> {{ t('config_perspective') }}</label>
              <label><input type="checkbox" v-model="config.scene_detect" /> {{ t('config_scene_detect') }}</label>
              <div class="strategy-row">
                <span>{{ t('config_default_intensity') }}</span>
                <button type="button" :class="{ active: config.preprocess_config.default_strategy === 'light' }" @click="config.preprocess_config.default_strategy = 'light'">{{ t('config_intensity_light') }}</button>
                <button type="button" :class="{ active: config.preprocess_config.default_strategy === 'standard' }" @click="config.preprocess_config.default_strategy = 'standard'">{{ t('config_intensity_standard') }}</button>
                <button type="button" :class="{ active: config.preprocess_config.default_strategy === 'heavy' }" @click="config.preprocess_config.default_strategy = 'heavy'">{{ t('config_intensity_deep') }}</button>
              </div>
              <label><input type="checkbox" v-model="config.preprocess_config.show_preview" /> {{ t('config_show_compare') }}</label>
              <label><input type="checkbox" v-model="config.preprocess_config.fallback_to_original" /> {{ t('config_fallback_original') }}</label>
              <label>{{ t('config_clahe_limit') }} <input class="inline-number" type="number" min="1" max="8" step="0.5" v-model.number="config.preprocess_config.advanced.clahe_clip_limit" /></label>
            </section>

            <section>
              <h4>{{ t('config_ai_refiner') }}</h4>
              <label><input type="checkbox" v-model="config.ai.enabled" /> {{ t('config_enable_ai') }}</label>
              <select v-model="config.ai.trigger_mode">
                <option value="auto">{{ t('config_ai_trigger_auto') }}</option>
                <option value="always">{{ t('config_ai_trigger_always') }}</option>
                <option value="manual">{{ t('config_ai_trigger_manual') }}</option>
              </select>
              <label><input type="checkbox" v-model="config.batch_ai_refine" /> {{ t('config_batch_ai_refine') }}</label>
              <p class="hint-text">{{ t('config_batch_ai_hint') }}</p>
              <button class="wide-action" type="button" @click="emit('open-ai-center')">{{ t('config_open_ai_center') }}</button>
            </section>

            <section>
              <h4>{{ t('config_output') }}</h4>
              <select v-model="config.output_mode">
                <option value="raw">{{ t('config_output_raw') }}</option>
                <option value="polished">{{ t('config_output_polished') }}</option>
                <option value="dual">{{ t('config_output_dual') }}</option>
                <option value="smart">{{ t('config_output_smart') }}</option>
              </select>
              <label><input type="checkbox" v-model="config.include_diff" /> {{ t('config_include_diff') }}</label>
            </section>

            <section>
              <h4>{{ t('config_startup') }}</h4>
              <label><input type="checkbox" v-model="config.preload_model" /> {{ t('config_preload_model') }}</label>
              <p class="hint-text">{{ t('config_preload_hint') }}</p>
            </section>

            <section>
              <h4>{{ t('config_notify') }}</h4>
              <label><input type="checkbox" v-model="config.notify_enabled" /> {{ t('config_notify_enabled') }}</label>
              <p class="hint-text">{{ t('config_notify_hint') }}</p>
              <button class="wide-action" type="button" @click="testNativeNotify">{{ t('config_test_notify') }}</button>
            </section>

            <section>
              <h4>{{ t('config_performance') }}</h4>
              <select v-model="config.power_mode">
                <option value="beast">{{ t('config_power_beast') }}</option>
                <option value="balanced">{{ t('config_power_balanced') }}</option>
                <option value="eco">{{ t('config_power_eco') }}</option>
              </select>
              <p class="hint-text">{{ t('config_power_hint') }}</p>
            </section>
          </div>

          <footer class="drawer-footer">
            <button class="secondary" type="button" @click="openDir">{{ t('config_open_models') }}</button>
            <button class="save-btn" type="button" @click="save" :disabled="configStore.isLoading">
              {{ configStore.isLoading ? t('config_saving') : t('config_save') }}
            </button>
          </footer>
        </aside>
      </div>
    </Transition>

  </Teleport>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { showToast } from '../composables/useToast'
import { notify } from '../composables/useNotify'
import ThemeControl from './ThemeControl.vue'
import { currentLang, setLang, t } from '../i18n'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible', 'open-ai-center', 'open-langpacks'])
const configStore = useConfigStore()

function close() {
  emit('update:visible', false)
}

const config = reactive({
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
  },
  output_mode: 'smart',
  include_diff: false,
  batch_ai_refine: false,
  power_mode: 'balanced',
  preprocess_config: {
    enabled: true,
    default_strategy: 'standard',
    show_preview: true,
    fallback_to_original: true,
    advanced: {
      clahe_clip_limit: 2.0,
      denoise_method: 'median',
    },
  },
})

watch(() => props.visible, (v) => {
  if (v) {
    Object.assign(config, JSON.parse(JSON.stringify(configStore.config)))
    config.preprocess_config ||= {}
    config.preprocess_config.default_strategy ||= 'standard'
    config.preprocess_config.show_preview ??= true
    config.preprocess_config.fallback_to_original ??= true
    config.preprocess_config.advanced ||= {}
    config.preprocess_config.advanced.clahe_clip_limit ??= 2.0
    config.preprocess_config.advanced.denoise_method ||= 'median'
  }
})

function openDir() {
  configStore.openModelsFolder()
}

async function testNativeNotify() {
  await notify({ title: 'VonishOCR', body: t('config_notify_test_body'), force: true })
  showToast({ type: 'success', message: t('toast_notify_sent'), duration: 2200 })
}

async function save() {
  try {
    await configStore.updateConfig(config)
    showToast({ type: 'success', message: t('toast_config_saved'), duration: 2000 })
    close()
  } catch (e) {
    showToast({ type: 'error', message: `${t('toast_config_save_failed')}: ${e.message}`, duration: 4000 })
  }
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 17, 15, 0.72);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: 400px;
  max-width: calc(100vw - 24px);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--v-rail);
  border-left: 1px solid var(--v-border);
  color: var(--v-text);
  font-family: var(--font-body);
}

.drawer-header {
  padding: var(--s5);
  border-bottom: 1px solid var(--v-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.drawer-title {
  margin-top: var(--s1);
  font-size: var(--fs-h2);
}

.close-btn {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  cursor: pointer;
}

.close-btn span,
.close-btn span::after {
  width: 14px;
  height: 1px;
  background: currentColor;
  display: block;
}

.close-btn span {
  transform: rotate(45deg);
}

.close-btn span::after {
  content: "";
  transform: rotate(90deg);
}

.close-btn:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
}

.drawer-body {
  flex: 1;
  padding: var(--s5);
  overflow-y: auto;
}

.drawer-body section {
  margin-bottom: var(--s5);
  padding: var(--s4);
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.drawer-body h4 {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  margin-bottom: var(--s3);
  letter-spacing: 0.04em;
}

.drawer-body label {
  display: flex;
  align-items: center;
  gap: var(--s2);
  margin: var(--s2) 0;
  font-size: var(--fs-small);
  color: var(--v-text-muted);
  cursor: pointer;
}

.drawer-body input[type='checkbox'] {
  accent-color: var(--v-accent);
}

.drawer-body input[type='text'],
.drawer-body input[type='password'],
.drawer-body input[type='number'],
.drawer-body select {
  width: 100%;
  min-height: 36px;
  padding: var(--s2) var(--s3);
  margin-top: var(--s2);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
  color: var(--v-text);
  font-family: var(--font-body);
  outline: none;
  transition: border-color var(--dur-base) var(--ease-cut);
}

.strategy-row {
  display: flex;
  align-items: center;
  gap: var(--s2);
  flex-wrap: wrap;
  margin-top: var(--s3);
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
}

.strategy-row button {
  min-height: 28px;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: transparent;
  color: var(--v-text-muted);
  cursor: pointer;
  padding-inline: var(--s2);
}

.strategy-row button.active {
  color: var(--v-text);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.inline-number {
  max-width: 96px;
}

.drawer-body input:focus,
.drawer-body select:focus {
  border-color: var(--v-accent);
}

.hint-text {
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  margin-top: var(--s2);
  line-height: 1.5;
}

.drawer-footer {
  padding: var(--s4) var(--s5);
  border-top: 1px solid var(--v-border);
  display: flex;
  gap: var(--s3);
}

.drawer-footer button {
  flex: 1;
  min-height: 36px;
  border-radius: var(--r3);
  cursor: pointer;
  font-weight: var(--fw-semibold);
}

.secondary {
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
}

.secondary:hover {
  color: var(--v-text);
  border-color: var(--v-border-strong);
}

.save-btn {
  background: var(--v-accent);
  color: var(--v-coal);
  border: 0;
}

.save-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.wide-action {
  width: 100%;
  min-height: 36px;
  margin-top: var(--s3);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
  color: var(--v-text);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  cursor: pointer;
}

.wide-action:hover {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.slide-enter-active,
.slide-leave-active {
  transition: opacity var(--dur-base) var(--ease-cut);
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}

</style>
