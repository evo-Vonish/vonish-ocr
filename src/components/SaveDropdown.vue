<template>
  <Teleport to="body">
    <Transition name="dropdown">
      <div v-if="visible" class="save-dropdown-overlay" @click.self="onCancel">
        <div ref="panelRef" class="save-dropdown-panel" :style="panelStyle">
          <div class="dropdown-title">保存选中</div>

          <div class="dropdown-section">
            <div class="section-label">文件格式</div>
            <div class="pill-group">
              <VButton
                v-for="f in formats"
                :key="f.key"
                type="ghost"
                size="sm"
                :active="format === f.key"
                @click="updateFormat(f.key)"
              >
                {{ f.label }}
              </VButton>
            </div>
          </div>

          <div class="dropdown-section">
            <div class="section-label">保存内容</div>
            <div class="pill-group">
              <VButton
                v-for="m in modes"
                :key="m.key"
                type="ghost"
                size="sm"
                :active="mode === m.key"
                @click="updateMode(m.key)"
              >
                {{ m.label }}
              </VButton>
            </div>
          </div>

          <div class="dropdown-section">
            <div class="section-label">文件名前缀</div>
            <input
              v-model="localPrefix"
              type="text"
              class="prefix-input"
              placeholder="vonish_ocr_result_"
              @keydown.stop
            />
          </div>

          <div class="dropdown-actions">
            <VButton type="ghost" size="sm" @click="onCancel">取消</VButton>
            <VButton type="primary" size="sm" @click="onConfirm">确认保存</VButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import VButton from './VButton.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  format: {
    type: String,
    default: 'md',
  },
  mode: {
    type: String,
    default: 'polished',
  },
  prefix: {
    type: String,
    default: 'vonish_ocr_result_',
  },
  anchorEl: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits([
  'update:visible',
  'update:format',
  'update:mode',
  'update:prefix',
  'confirm',
  'cancel',
])

const formats = [
  { key: 'txt', label: 'TXT' },
  { key: 'md', label: 'MD' },
  { key: 'docx', label: 'DOCX' },
]

const modes = [
  { key: 'raw', label: '原文本' },
  { key: 'polished', label: '修复后' },
  { key: 'compare', label: '双结果对比' },
]

const panelRef = ref(null)
const localPrefix = ref(props.prefix)

watch(() => props.visible, (v) => {
  if (v) {
    localPrefix.value = props.prefix
    computePosition()
    document.addEventListener('keydown', onEsc)
  } else {
    document.removeEventListener('keydown', onEsc)
  }
})

watch(() => props.prefix, (v) => {
  localPrefix.value = v
})

const panelStyle = ref({})

function computePosition() {
  if (!props.anchorEl) {
    panelStyle.value = { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
    return
  }
  const rect = props.anchorEl.getBoundingClientRect()
  const panelWidth = 280
  let left = rect.left
  if (left + panelWidth > window.innerWidth - 16) {
    left = window.innerWidth - panelWidth - 16
  }
  panelStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 8}px`,
    left: `${left}px`,
    width: `${panelWidth}px`,
  }
}

function updateFormat(val) {
  emit('update:format', val)
}

function updateMode(val) {
  emit('update:mode', val)
}

function onConfirm() {
  emit('update:prefix', localPrefix.value)
  emit('confirm', {
    format: props.format,
    mode: props.mode,
    prefix: localPrefix.value,
  })
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
.save-dropdown-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
}

.save-dropdown-panel {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s4);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  gap: var(--s4);
}

.dropdown-title {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  font-weight: var(--fw-semibold);
  color: var(--v-text);
}

.dropdown-section {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
}

.section-label {
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.pill-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s1);
}

.prefix-input {
  width: 100%;
  height: 32px;
  padding-inline: var(--s2);
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  outline: none;
  transition: border-color 0.15s var(--ease-cut);
}

.prefix-input:focus {
  border-color: var(--v-accent);
}

.prefix-input::placeholder {
  color: var(--v-text-faint);
}

.dropdown-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--s2);
  margin-top: var(--s1);
}

/* 动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s ease-out;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
}

.dropdown-enter-active .save-dropdown-panel,
.dropdown-leave-active .save-dropdown-panel {
  transition: transform 0.2s ease-out, opacity 0.2s ease-out;
}

.dropdown-enter-from .save-dropdown-panel,
.dropdown-leave-to .save-dropdown-panel {
  transform: translateY(-8px);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .dropdown-enter-active,
  .dropdown-leave-active,
  .dropdown-enter-active .save-dropdown-panel,
  .dropdown-leave-active .save-dropdown-panel {
    transition: none;
  }
}
</style>
