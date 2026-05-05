<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <section class="provider-modal" role="dialog" aria-modal="true" aria-label="API 方案中心">
          <header class="modal-head">
            <div>
              <div class="modal-kicker">AI PROVIDER CENTER</div>
              <h2 class="modal-title v-title">API 方案中心</h2>
            </div>
            <button class="close-btn" type="button" title="关闭" @click="close">
              <span aria-hidden="true"></span>
            </button>
          </header>
          <div class="modal-body">
            <AIProviderCenter layout="wide" />
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import AIProviderCenter from './AIProviderCenter.vue'

defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])

function close() {
  emit('update:visible', false)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: var(--s6);
  background: rgba(17, 17, 15, 0.78);
}

.provider-modal {
  width: min(1040px, calc(100vw - 48px));
  max-height: min(780px, calc(100vh - 48px));
  display: flex;
  flex-direction: column;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  color: var(--v-text);
  overflow: hidden;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--s4);
  padding: var(--s5);
  border-bottom: 1px solid var(--v-border);
}

.modal-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.modal-title {
  margin-top: var(--s1);
  font-size: var(--fs-h1);
}

.modal-body {
  padding: var(--s5);
  overflow: auto;
}

.close-btn {
  width: 34px;
  height: 34px;
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) var(--ease-cut);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
