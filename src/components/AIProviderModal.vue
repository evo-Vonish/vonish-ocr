<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="lab-overlay" @click.self="close">
        <section class="lab-modal" role="dialog" aria-modal="true" aria-label="API 方案中心">
          <header class="lab-head">
            <div>
              <div class="lab-kicker">AI PROVIDER CENTER</div>
              <h2 class="lab-title v-title">API 方案中心</h2>
            </div>
            <button class="close-btn" type="button" title="关闭" @click="close">
              <span aria-hidden="true"></span>
            </button>
          </header>

          <div class="lab-body">
            <aside class="lab-rail">
              <div class="section-kicker">SAVED SCHEMES</div>
              <span class="scheme-count-badge">{{ schemes.length.toString().padStart(2, '0') }}</span>
              <p class="rail-desc">
                创建并管理 AI 精修方案。故障切换会按权重依次尝试；Key 由后端加密存储，不写入 localStorage。
              </p>
              <button type="button" class="primary-action" @click="centerRef?.startCreate()">
                + 创建方案
              </button>
              <div class="rail-footer">
                <div class="provider-legend">
                  <span>DeepSeek</span><span>ChatGPT</span><span>Claude</span><span>Gemini</span><span>Qwen</span><span>豆包</span>
                </div>
                <div class="failover-hint">
                  遇到 404 / 429 / 5xx / 超时后延迟 500ms，按权重尝试下一家。
                </div>
              </div>
            </aside>

            <main class="lab-main">
              <AIProviderCenter ref="centerRef" layout="wide" />
            </main>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'
import AIProviderCenter from './AIProviderCenter.vue'
import { useConfigStore } from '../stores/configStore'

defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])
const configStore = useConfigStore()
const centerRef = ref(null)

const schemes = computed(() => configStore.aiSchemes)

function close() {
  emit('update:visible', false)
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
  overflow: hidden;
}

.lab-rail,
.lab-main {
  background: var(--v-panel);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r4);
  overflow: hidden;
}

.lab-rail {
  display: flex;
  flex-direction: column;
  gap: var(--s4);
  padding: var(--s5);
  overflow-y: auto;
}

.scheme-count-badge {
  font-family: var(--font-mono);
  font-size: var(--fs-display);
  color: var(--v-accent);
  line-height: 1;
}

.rail-desc {
  margin: 0;
  color: var(--v-text-muted);
  font-size: var(--fs-small);
  line-height: 1.7;
}

.primary-action {
  min-height: 40px;
  border: 0;
  border-radius: var(--r3);
  background: var(--v-accent);
  color: var(--v-coal);
  font-weight: var(--fw-semibold);
  cursor: pointer;
}

.primary-action:hover {
  background: color-mix(in srgb, var(--v-accent) 80%, white);
}

.rail-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}

.provider-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s1);
}

.provider-legend span {
  padding: 2px 8px;
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r1);
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--v-text-faint);
}

.failover-hint {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-text-faint);
  line-height: 1.55;
  letter-spacing: 0.03em;
}

.lab-main {
  overflow-y: auto;
}

.close-btn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  background: transparent;
  border: var(--v-border-width) solid var(--v-border);
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) var(--ease-cut);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 760px) {
  .lab-body {
    grid-template-columns: 1fr;
  }

  .lab-rail {
    max-height: 200px;
  }
}
</style>
