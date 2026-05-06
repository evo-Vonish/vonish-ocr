<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div v-if="visible" class="confirm-overlay" @click.self="onCancel">
        <div class="confirm-panel">
          <div class="confirm-head">
            <span class="confirm-title">{{ title }}</span>
          </div>
          <div class="confirm-body">{{ message }}</div>
          <div class="confirm-foot">
            <VButton type="ghost" @click="onCancel">{{ cancelText }}</VButton>
            <VButton :type="confirmType" @click="onConfirm">{{ confirmText }}</VButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import VButton from './VButton.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: '确认',
  },
  message: {
    type: String,
    default: '',
  },
  confirmText: {
    type: String,
    default: '确定',
  },
  cancelText: {
    type: String,
    default: '取消',
  },
  confirmType: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'danger'].includes(v),
  },
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

watch(() => props.visible, (v) => {
  if (v) {
    document.addEventListener('keydown', onEsc)
  } else {
    document.removeEventListener('keydown', onEsc)
  }
})

function onConfirm() {
  emit('confirm')
  emit('update:visible', false)
}

function onCancel() {
  emit('cancel')
  emit('update:visible', false)
}

function onEsc(e) {
  if (e.key === 'Escape') {
    onCancel()
  }
}

onMounted(() => {
  if (props.visible) document.addEventListener('keydown', onEsc)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEsc)
})
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 17, 15, 0.72);
  z-index: 10000;
  display: grid;
  place-items: center;
  padding: var(--s5);
}

.confirm-panel {
  width: 100%;
  max-width: 400px;
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s5);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
}

.confirm-head {
  margin-bottom: var(--s3);
}

.confirm-title {
  font-family: var(--font-title);
  font-size: var(--fs-h2);
  color: var(--v-text);
}

.confirm-body {
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  line-height: 1.6;
  margin-bottom: var(--s5);
  word-break: break-word;
}

.confirm-foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--s3);
}

/* 动画 */
.confirm-enter-active,
.confirm-leave-active {
  transition: all var(--dur-base) var(--ease-cut);
}

.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}

.confirm-enter-active .confirm-panel,
.confirm-leave-active .confirm-panel {
  transition: all var(--dur-base) var(--ease-cut);
}

.confirm-enter-from .confirm-panel,
.confirm-leave-to .confirm-panel {
  opacity: 0;
  transform: scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .confirm-enter-active,
  .confirm-leave-active,
  .confirm-enter-active .confirm-panel,
  .confirm-leave-active .confirm-panel {
    transition: none;
  }
}
</style>
