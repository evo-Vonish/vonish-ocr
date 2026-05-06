<template>
  <span
    :class="['v-checkbox', { checked: isChecked, indeterminate: isIndeterminate, disabled }]"
    role="checkbox"
    :aria-checked="ariaChecked"
    tabindex="0"
    @click="toggle"
    @keydown.space.prevent="toggle"
  >
    <svg
      v-if="isChecked"
      class="check-icon"
      viewBox="0 0 12 12"
      width="12"
      height="12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M2 6.5L4.5 9L10 3.5"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
    <svg
      v-else-if="isIndeterminate"
      class="check-icon"
      viewBox="0 0 12 12"
      width="12"
      height="12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M3 6H9"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
      />
    </svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  checked: {
    type: Boolean,
    default: false,
  },
  indeterminate: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:checked', 'change'])

const isChecked = computed(() => props.checked && !props.indeterminate)
const isIndeterminate = computed(() => props.indeterminate)

const ariaChecked = computed(() => {
  if (props.indeterminate) return 'mixed'
  return props.checked ? 'true' : 'false'
})

function toggle() {
  if (props.disabled) return
  const newVal = !props.checked
  emit('update:checked', newVal)
  emit('change', newVal)
}
</script>

<style scoped>
.v-checkbox {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--v-border);
  border-radius: var(--r1);
  background: var(--v-bg);
  color: var(--v-text);
  cursor: pointer;
  transition:
    border-color 0.15s var(--ease-cut),
    background-color 0.15s var(--ease-cut);
}

.v-checkbox:hover:not(.disabled) {
  border-color: var(--v-border-strong);
}

.v-checkbox.checked,
.v-checkbox.indeterminate {
  border-color: var(--v-accent);
  background: var(--v-accent-16);
}

.v-checkbox.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.check-icon {
  width: 12px;
  height: 12px;
  animation: checkPop 200ms cubic-bezier(.2, 1.6, .35, 1) forwards;
}

@keyframes checkPop {
  0% { transform: scale(0.8); opacity: 0; }
  70% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .v-checkbox {
    transition: none;
  }
  .check-icon {
    animation: none;
  }
}
</style>
