<template>
  <section class="case-vault">
    <header class="vault-top">
      <div class="vault-heading">
        <span class="breath-dot" aria-hidden="true"></span>
        <div>
          <h1 class="vault-title v-title">案卷库</h1>
          <div class="vault-kicker">CASE VAULT · LOCAL ARCHIVE</div>
        </div>
      </div>
      <div class="vault-top-right">
        <SearchFilter v-model:search="search" v-model:filters="filters" />
        <button class="return-btn" type="button" @click="$emit('close')">← 返回证据桌</button>
      </div>
    </header>

    <main class="vault-body">
      <EmptyVault v-if="!evidences.total && !loading" @go-desk="$emit('close')" />

      <template v-else>
        <BatchActionBar
          v-if="selectedIds.length"
          :count="selectedIds.length"
          @close="clearSelection"
          @delete="batchDelete"
          @export="batchExport"
          @move="showMoveDialog = true"
        />

        <div class="vault-grid">
          <aside class="vault-sessions">
            <SessionList
              :sessions="sessions"
              :active-id="activeSessionId"
              @select="onSelectSession"
              @create="onCreateSession"
            />
          </aside>

          <main class="vault-timeline">
            <EvidenceTimeline
              :evidences="evidences.items"
              :loading="loading"
              :selected-ids="selectedIds"
              @select="onSelectEvidence"
              @toggle="onToggleSelect"
            />
          </main>

          <aside v-if="detailEvidence" class="vault-detail">
            <EvidenceDetail
              :evidence="detailEvidence"
              @close="detailEvidence = null"
              @reprocess="onReprocess"
              @export="exportSingle"
              @move="showMoveDialog = true"
              @delete="deleteSingle"
            />
          </aside>
        </div>
      </template>
    </main>

    <div v-if="showMoveDialog" class="console-dialog-backdrop" @click.self="showMoveDialog = false">
      <section class="console-dialog" role="dialog">
        <div class="console-dialog-title v-title">移至案件组</div>
        <div class="session-pick-list">
          <button v-for="s in sessions" :key="s.id" class="session-pick" :class="{ active: moveTargetId === s.id }" @click="moveTargetId = s.id">
            {{ s.name }}
          </button>
        </div>
        <div class="console-dialog-actions">
          <button class="secondary-btn" type="button" @click="showMoveDialog = false">取消</button>
          <button class="primary-btn" type="button" @click="confirmMove">确认移动</button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPythonPort, getConfig } from '../api/tauri_ipc'
import SessionList from '../components/vault/SessionList.vue'
import EvidenceTimeline from '../components/vault/EvidenceTimeline.vue'
import EvidenceDetail from '../components/vault/EvidenceDetail.vue'
import SearchFilter from '../components/vault/SearchFilter.vue'
import BatchActionBar from '../components/vault/BatchActionBar.vue'
import EmptyVault from '../components/vault/EmptyVault.vue'
import { showToast } from '../composables/useToast'

defineEmits(['close'])

const sessions = ref([])
const evidences = ref({ total: 0, items: [] })
const loading = ref(true)
const activeSessionId = ref('')
const search = ref('')
const filters = ref({ scene_type: '', model_tier: '', status: '' })
const selectedIds = ref([])
const detailEvidence = ref(null)
const showMoveDialog = ref(false)
const moveTargetId = ref('')

let backendPort = 8000

onMounted(async () => {
  const cfg = await getConfig().catch(() => ({}))
  const savedPort = cfg?.port || 8000
  backendPort = savedPort
  await loadSessions()
  await loadEvidences()
})

async function api(path, opts = {}) {  const url = `http://127.0.0.1:${backendPort}${path}`
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

async function loadSessions() {
  try { sessions.value = await api('/vault/sessions') } catch (e) { console.warn('load sessions failed', e) }
}

async function loadEvidences() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (activeSessionId.value) params.set('session_id', activeSessionId.value)
    if (search.value) params.set('search', search.value)
    if (filters.value.scene_type) params.set('scene_type', filters.value.scene_type)
    if (filters.value.model_tier) params.set('model_tier', filters.value.model_tier)
    if (filters.value.status) params.set('status', filters.value.status)
    params.set('limit', '100')
    evidences.value = await api(`/vault/evidences?${params}`)
  } catch (e) {
    console.warn('load evidences failed', e)
    evidences.value = { total: 0, items: [] }
  } finally { loading.value = false }
}

function onSelectSession(id) {
  activeSessionId.value = id
  detailEvidence.value = null
  selectedIds.value = []
  loadEvidences()
}

async function onCreateSession(name) {
  try {
    await api('/vault/sessions', { method: 'POST', body: JSON.stringify({ name }) })
    await loadSessions()
    showToast({ type: 'success', message: '案件组已创建', duration: 2000 })
  } catch (e) { showToast({ type: 'error', message: '创建失败', duration: 3000 }) }
}

async function onSelectEvidence(item) {
  try {
    detailEvidence.value = await api(`/vault/evidences/${item.id}`)
  } catch (e) { console.warn('load detail failed', e) }
}

function onToggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function clearSelection() { selectedIds.value = [] }

async function batchDelete() {
  if (!confirm(`确认永久删除 ${selectedIds.value.length} 条证据？此操作不可撤销。`)) return
  try {
    await api('/vault/evidences/batch-delete', { method: 'POST', body: JSON.stringify({ evidence_ids: selectedIds.value }) })
    clearSelection()
    await loadEvidences()
    showToast({ type: 'success', message: '已删除', duration: 2000 })
  } catch (e) { showToast({ type: 'error', message: '删除失败', duration: 3000 }) }
}

async function batchExport() {
  showToast({ type: 'info', message: '导出功能开发中', duration: 2000 })
}

async function deleteSingle() {
  if (!detailEvidence.value || !confirm('确认删除此证据？')) return
  try {
    await api(`/vault/evidences/${detailEvidence.value.id}`, { method: 'DELETE' })
    detailEvidence.value = null
    await loadEvidences()
    showToast({ type: 'success', message: '已删除', duration: 2000 })
  } catch (e) { showToast({ type: 'error', message: '删除失败', duration: 3000 }) }
}

async function confirmMove() {
  try {
    await api('/vault/evidences/move-to-session', {
      method: 'POST',
      body: JSON.stringify({ evidence_ids: selectedIds.value.length ? selectedIds.value : [detailEvidence.value?.id], session_id: moveTargetId.value || null }),
    })
    showMoveDialog.value = false
    clearSelection()
    detailEvidence.value = null
    await loadEvidences()
    showToast({ type: 'success', message: '已移动', duration: 2000 })
  } catch (e) { showToast({ type: 'error', message: '移动失败', duration: 3000 }) }
}

function exportSingle() { batchExport() }

function onReprocess() {
  showToast({ type: 'info', message: '重新识别将加入证据桌队列', duration: 2000 })
}
</script>

<style scoped>
.case-vault {
  height: 100vh;
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr);
  gap: var(--layout-gap);
  padding: var(--layout-pad);
  background: var(--v-bg);
  color: var(--v-text);
  overflow: hidden;
  animation: vault-in 200ms var(--ease-cut);
}

@keyframes vault-in { from { opacity: 0; } to { opacity: 1; } }

.vault-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding-inline: var(--s4);
}

.vault-top-right { display: flex; align-items: center; gap: var(--s3); }

.vault-heading { display: flex; align-items: center; gap: var(--s3); }

.breath-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--v-accent);
  box-shadow: 0 0 12px var(--v-accent-32);
  animation: dot-breath 1600ms var(--ease-cut) infinite;
}

@keyframes dot-breath {
  0%, 100% { opacity: 0.42; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1); }
}

.vault-kicker {
  margin-top: 2px;
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.vault-title { margin: 0; font-size: 24px; }

.return-btn {
  min-height: 36px;
  padding-inline: var(--s4);
  background: transparent;
  color: var(--v-text);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  font-family: var(--font-title);
  cursor: pointer;
}

.return-btn:hover { border-color: var(--v-accent); box-shadow: var(--glow-soft); }

.vault-body { min-height: 0; overflow: hidden; }

.vault-grid {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 320px;
  gap: var(--s4);
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.vault-grid:has(.vault-detail:empty) { grid-template-columns: 240px minmax(0, 1fr) 0; }
.vault-grid:has(.vault-detail:not(:empty)) { grid-template-columns: 240px minmax(0, 1fr) 320px; }

.vault-sessions, .vault-detail {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  overflow-y: auto;
  padding: var(--s3);
}

.vault-timeline {
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  overflow-y: auto;
  padding: var(--s4);
}

/* dialog */
.console-dialog-backdrop {
  position: fixed; inset: 0; z-index: 100;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--v-bg) 78%, transparent);
}

.console-dialog {
  width: min(420px, calc(100vw - 48px));
  background: var(--v-rail);
  border: 1px solid var(--v-border-strong);
  border-radius: var(--r4);
  padding: var(--s5);
}

.console-dialog-title { font-size: var(--fs-h2); margin-bottom: var(--s3); }

.console-dialog-actions { display: flex; justify-content: flex-end; gap: var(--s3); margin-top: var(--s5); }

.secondary-btn, .primary-btn {
  min-height: 34px; padding-inline: var(--s3);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: transparent;
  color: var(--v-text-muted);
  cursor: pointer;
}

.primary-btn { background: var(--v-accent); border-color: var(--v-accent); color: var(--v-coal); }

.session-pick-list { display: flex; flex-direction: column; gap: var(--s2); margin: var(--s3) 0; }

.session-pick {
  padding: var(--s2) var(--s3);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: transparent;
  color: var(--v-text);
  text-align: left;
  cursor: pointer;
}

.session-pick.active { border-color: var(--v-accent); box-shadow: var(--glow-soft); }
</style>
