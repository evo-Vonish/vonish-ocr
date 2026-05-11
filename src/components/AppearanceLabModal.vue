<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="lab-overlay" @click.self="close">
        <section class="lab-modal" role="dialog" aria-modal="true" aria-label="外观实验室">
          <header class="lab-head">
            <div>
              <div class="lab-kicker">APPEARANCE LAB</div>
              <h2 class="lab-title v-title">{{ t('theme_appearance_lab') }}</h2>
            </div>
            <button class="close-btn" type="button" :title="t('btn_close')" @click="close">
              <span aria-hidden="true"></span>
            </button>
          </header>

          <div class="lab-body">
            <aside class="lab-rail">
              <div class="section-kicker">THEME TOKENS</div>
              <p>{{ railCopy }}</p>
              <label class="toggle-row">
                <input type="checkbox" :checked="themeStore.customTokens.enabled" @change="themeStore.setCustomToken('enabled', $event.target.checked)" />
                <span>{{ t('theme_custom_enable') }}</span>
              </label>
              <button class="ghost-action" type="button" @click="themeStore.resetCustomTokens()">
                {{ t('theme_reset') }}
              </button>
            </aside>

            <main class="token-board">
              <div class="preview-panel">
                <div class="preview-swatches">
                  <span class="swatch bg"></span>
                  <span class="swatch rail"></span>
                  <span class="swatch text"></span>
                  <span class="swatch accent"></span>
                </div>
                <div>
                  <div class="preview-title">{{ previewTitle }}</div>
                  <div class="preview-copy">{{ previewCopy }}</div>
                </div>
              </div>

              <div class="token-grid">
                <label>
                  <span>{{ t('theme_token_accent') }}</span>
                  <input :value="themeStore.customTokens.accent" maxlength="7" @change="setHex('accent', $event.target.value)" />
                </label>
                <label>
                  <span>{{ t('theme_token_warn') }}</span>
                  <input :value="themeStore.customTokens.warn" maxlength="7" @change="setHex('warn', $event.target.value)" />
                </label>
                <label>
                  <span>{{ t('theme_token_error') }}</span>
                  <input :value="themeStore.customTokens.error" maxlength="7" @change="setHex('error', $event.target.value)" />
                </label>
                <label>
                  <span>{{ t('theme_token_success') }}</span>
                  <input :value="themeStore.customTokens.success" maxlength="7" @change="setHex('success', $event.target.value)" />
                </label>
              </div>
            </main>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useThemeStore } from '../stores/themeStore'
import { currentLang, t } from '../i18n'
import { showToast } from '../composables/useToast'

defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])
const themeStore = useThemeStore()

const isZh = computed(() => currentLang.value === 'zh')
const names = computed(() => ({
  evidence: t('theme_style_evidence'),
  professional: t('theme_style_professional'),
  hc: t('theme_style_hc'),
  dark: t('theme_mode_dark'),
  light: t('theme_mode_light'),
}))

const previewTitle = computed(() => {
  if (themeStore.resolvedHighContrast) return t('theme_style_hc')
  return `${names.value[themeStore.resolvedAppearance]} / ${names.value[themeStore.resolvedMode]}`
})

const previewCopy = computed(() => {
  if (themeStore.resolvedHighContrast) return t('theme_preview_hc')
  if (themeStore.resolvedAppearance === 'professional') return t('theme_preview_professional')
  return t('theme_preview_evidence')
})

const railCopy = computed(() => isZh.value
  ? '这里只调整安全的颜色令牌，不改布局尺寸，也不会写入业务配置。输入必须是 6 位 HEX。'
  : 'Only safe color tokens are editable here. Layout sizes stay fixed, and values must be 6-digit HEX colors.'
)

function close() {
  emit('update:visible', false)
}

function setHex(key, value) {
  if (!/^#[0-9A-Fa-f]{6}$/.test(String(value || '').trim())) {
    showToast({ type: 'error', message: t('theme_hex_error') })
    return
  }
  themeStore.setCustomToken(key, value)
}
</script>

<style scoped>
.lab-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: var(--s6);
  background: rgba(17, 17, 15, 0.78);
}

.lab-modal {
  width: min(1040px, calc(100vw - 48px));
  max-height: min(760px, calc(100vh - 48px));
  display: flex;
  flex-direction: column;
  background: var(--v-rail);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r4);
  color: var(--v-text);
  overflow: hidden;
}

.lab-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--s4);
  padding: var(--s5);
  border-bottom: var(--v-border-width) solid var(--v-border);
}

.lab-kicker,
.section-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.lab-title {
  margin-top: var(--s1);
  font-size: var(--fs-h1);
}

.lab-body {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: var(--s5);
  padding: var(--s5);
  overflow: auto;
}

.lab-rail,
.token-board {
  background: var(--v-panel);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r4);
}

.lab-rail {
  display: flex;
  flex-direction: column;
  gap: var(--s4);
  padding: var(--s5);
}

.lab-rail p {
  margin: 0;
  color: var(--v-text-muted);
  font-size: var(--fs-small);
  line-height: 1.7;
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

.token-board {
  padding: var(--s5);
}

.preview-panel {
  min-height: 110px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: var(--s4);
  padding: var(--s4);
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
}

.preview-swatches {
  display: flex;
  gap: var(--s1);
}

.swatch {
  width: 28px;
  height: 58px;
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r2);
}

.swatch.bg { background: var(--v-bg); }
.swatch.rail { background: var(--v-rail); }
.swatch.text { background: var(--v-text); }
.swatch.accent { background: var(--v-accent); }

.preview-title {
  color: var(--v-text);
  font-size: var(--fs-h2);
  font-weight: var(--fw-semibold);
}

.preview-copy {
  margin-top: var(--s1);
  color: var(--v-text-muted);
  font-size: var(--fs-small);
}

.token-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s4);
  margin-top: var(--s5);
}

.token-grid label {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  color: var(--v-text-muted);
  font-size: var(--fs-small);
}

.token-grid input {
  min-height: 38px;
  padding: 0 var(--s3);
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text);
  font-family: var(--font-mono);
}

.ghost-action,
.close-btn {
  background: transparent;
  color: var(--v-text-muted);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  cursor: pointer;
}

.ghost-action {
  min-height: 38px;
}

.close-btn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
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

.ghost-action:hover,
.close-btn:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) var(--ease-cut);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 760px) {
  .lab-body,
  .token-grid {
    grid-template-columns: 1fr;
  }
}
</style>
