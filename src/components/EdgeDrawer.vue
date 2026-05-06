<template>
  <Teleport to="body">
    <div v-if="visible" class="edge-drawer-backdrop" @click="close" />
    <div
      class="edge-drawer"
      :class="[`side-${side}`, { open: visible }]"
      :style="{ width: drawerWidth }"
    >
      <div class="drawer-body">
        <slot />
      </div>
    </div>
    <div
      v-if="!visible"
      class="edge-trigger"
      :class="`trigger-${side}`"
      @click="open"
    >
      <span class="trigger-hint"></span>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  side: { type: String, default: 'left', validator: v => ['left', 'right'].includes(v) },
  width: { type: String, default: '40%' },
})
const emit = defineEmits(['open', 'close'])

const drawerWidth = props.width

function open() {
  emit('open')
}

function close() {
  emit('close')
}
</script>

<style scoped>
.edge-drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 98;
  background: color-mix(in srgb, var(--v-bg) 60%, transparent);
  animation: backdrop-in 0.3s ease;
}

@keyframes backdrop-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.edge-drawer {
  position: fixed;
  top: 0;
  bottom: 0;
  z-index: 99;
  background: var(--v-rail);
  border: 1px solid var(--v-border-strong);
  overflow-y: auto;
  transition: transform 0.3s cubic-bezier(0.2, 0, 0.1, 1);
}

.edge-drawer.side-left {
  left: 0;
  border-right-width: 1px;
  transform: translateX(-100%);
}

.edge-drawer.side-right {
  right: 0;
  border-left-width: 1px;
  transform: translateX(100%);
}

.edge-drawer.open {
  transform: translateX(0);
}

.drawer-body {
  padding: var(--space-md);
  min-height: 100%;
}

/* 边缘触发区 */
.edge-trigger {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  width: 20px;
  height: 80px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.edge-trigger.trigger-left {
  left: 0;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.edge-trigger.trigger-right {
  right: 0;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.trigger-hint {
  width: 3px;
  height: 32px;
  background: var(--v-border-strong);
  border-radius: 2px;
  transition: background 0.2s;
}

.edge-trigger:hover .trigger-hint {
  background: var(--v-accent);
}
</style>
