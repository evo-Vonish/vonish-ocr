<template>
  <div class="session-list">
    <div class="session-label">案件组</div>
    <div
      v-for="s in sessions"
      :key="s.id"
      class="session-item"
      :class="{ active: s.id === activeId }"
      @click="$emit('select', s.id)"
    >
      <span class="session-name">{{ s.name }}</span>
      <span class="session-count">{{ s.count }}</span>
    </div>
    <div class="new-session">
      <input
        v-if="creating"
        ref="newInput"
        v-model="newName"
        class="new-input"
        placeholder="案件组名称"
        @keyup.enter="confirmCreate"
        @blur="cancelCreate"
      />
      <button v-else class="new-btn" type="button" @click="startCreate">+ 新建案件组</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: String, default: '' },
})
const emit = defineEmits(['select', 'create'])

const creating = ref(false)
const newName = ref('')
const newInput = ref(null)

async function startCreate() {
  creating.value = true
  await nextTick()
  newInput.value?.focus()
}

function confirmCreate() {
  if (newName.value.trim()) emit('create', newName.value.trim())
  newName.value = ''
  creating.value = false
}

function cancelCreate() {
  newName.value = ''
  creating.value = false
}
</script>

<style scoped>
.session-list { display: flex; flex-direction: column; gap: 2px; }

.session-label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
  padding: 0 var(--s2) var(--s2);
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding-inline: var(--s3);
  border-left: 2px solid transparent;
  border-radius: 0 var(--r2) var(--r2) 0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.session-item:hover { background: var(--v-panel); }

.session-item.active {
  background: var(--v-panel);
  border-left-color: var(--v-accent);
  color: var(--v-text);
}

.session-name {
  font-size: 14px;
  color: inherit;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-text-muted);
  flex-shrink: 0;
}

.new-session { margin-top: var(--s2); }

.new-btn {
  width: 100%;
  height: 36px;
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  font-size: var(--fs-caption);
  cursor: pointer;
  transition: border-color 0.15s;
}

.new-btn:hover { border-color: var(--v-accent); color: var(--v-text); }

.new-input {
  width: 100%;
  height: 36px;
  padding-inline: var(--s2);
  background: var(--v-bg);
  border: 1px solid var(--v-accent);
  border-radius: var(--r2);
  color: var(--v-text);
  font-size: var(--fs-caption);
}
</style>
