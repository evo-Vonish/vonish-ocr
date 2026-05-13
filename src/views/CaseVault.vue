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
        <button class="return-btn" type="button" @click="$emit('close')">返回证据桌</button>
      </div>
    </header>

    <main class="vault-body">
      <EmptyVault v-if="!evidences.total && !loading" @go-desk="$emit('close')" />

      <template v-else>
        <BatchActionBar
          v-if="selectedIds.length"
          :count="selectedIds.length"
          @close="clearSelection"
          @delete="requestBatchDelete"
          @export="batchExport"
          @move="openMoveDialog"
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
              :backend-base="backendBase"
              @select="onSelectEvidence"
              @toggle="onToggleSelect"
            />
          </main>

          <aside v-if="detailEvidence" class="vault-detail">
            <EvidenceDetail
              :evidence="detailEvidence"
              :backend-base="backendBase"
              @close="detailEvidence = null"
              @reprocess="onReprocess"
              @export="exportSingle"
              @move="openMoveDialog"
              @delete="requestSingleDelete"
            />
          </aside>
        </div>
      </template>
    </main>

    <div v-if="showMoveDialog" class="console-dialog-backdrop" @click.self="showMoveDialog = false">
      <section class="console-dialog" role="dialog" aria-modal="true">
        <div class="console-dialog-title v-title">移至案卷组</div>
        <div class="session-pick-list">
          <button
            class="session-pick"
            :class="{ active: moveTargetId === null }"
            type="button"
            @click="moveTargetId = null"
          >
            未分组
          </button>
          <button
            v-for="s in moveSessions"
            :key="s.id"
            class="session-pick"
            :class="{ active: moveTargetId === s.id }"
            type="button"
            @click="moveTargetId = s.id"
          >
            {{ s.name }}
          </button>
        </div>
        <div class="console-dialog-actions">
          <button class="secondary-btn" type="button" @click="showMoveDialog = false">取消</button>
          <button class="primary-btn" type="button" @click="confirmMove">确认移动</button>
        </div>
      </section>
    </div>

    <div v-if="confirmDialog.open" class="console-dialog-backdrop" @click.self="closeConfirm">
      <section class="console-dialog" role="dialog" aria-modal="true">
        <div class="console-dialog-title v-title">{{ confirmDialog.title }}</div>
        <p class="confirm-copy">{{ confirmDialog.message }}</p>
        <div class="console-dialog-actions">
          <button class="secondary-btn" type="button" @click="closeConfirm">取消</button>
          <button class="danger-btn" type="button" @click="runConfirm">确认</button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { getPythonPort } from '../api/tauri_ipc'
import SessionList from '../components/vault/SessionList.vue'
import EvidenceTimeline from '../components/vault/EvidenceTimeline.vue'
import EvidenceDetail from '../components/vault/EvidenceDetail.vue'
import SearchFilter from '../components/vault/SearchFilter.vue'
import BatchActionBar from '../components/vault/BatchActionBar.vue'
import EmptyVault from '../components/vault/EmptyVault.vue'
import { showToast } from '../composables/useToast'
import { downloadBlob } from '../utils/exporters'

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
const moveTargetId = ref(null)
const backendBase = ref('http://127.0.0.1:8000')
const confirmDialog = reactive({ open: false, title: '', message: '', action: null })

const activeSession = computed(() => sessions.value.find(s => s.id === activeSessionId.value))
const moveSessions = computed(() => sessions.value.filter(s => !s.is_default && s.name !== '未分组'))

let searchTimer = null

onMounted(async () => {
  await resolveBackend()
  await loadSessions()
  const defaultSession = sessions.value.find(s => s.is_default) || sessions.value[0]
  activeSessionId.value = defaultSession?.id || ''
  await loadEvidences()
})

watch([search, filters], () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    selectedIds.value = []
    loadEvidences()
  }, 220)
}, { deep: true })

async function resolveBackend() {
  const port = await getPythonPort().catch(() => 8000)
  backendBase.value = `http://127.0.0.1:${port || 8000}`
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) }
  if (opts.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${backendBase.value}${path}`, { ...opts, headers })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

async function loadSessions() {
  try {
    sessions.value = await api('/vault/sessions')
  } catch (e) {
    console.warn('load sessions failed', e)
    showToast({ type: 'error', message: '案卷组加载失败', duration: 3000 })
  }
}

function buildListParams() {
  const params = new URLSearchParams()
  if (activeSession.value?.is_default) {
    // “全部证据”不发送 session_id，后端返回全量。
  } else if (activeSession.value?.name === '未分组') {
    params.set('session_id', '')
  } else if (activeSessionId.value) {
    params.set('session_id', activeSessionId.value)
  }
  if (search.value) params.set('search', search.value)
  if (filters.value.scene_type) params.set('scene_type', filters.value.scene_type)
  if (filters.value.model_tier) params.set('model_tier', filters.value.model_tier)
  if (filters.value.status) params.set('status', filters.value.status)
  params.set('limit', '100')
  return params
}

async function loadEvidences() {
  loading.value = true
  try {
    evidences.value = await api(`/vault/evidences?${buildListParams()}`)
  } catch (e) {
    console.warn('load evidences failed', e)
    evidences.value = { total: 0, items: [] }
    showToast({ type: 'error', message: '证据列表加载失败', duration: 3000 })
  } finally {
    loading.value = false
  }
}

function onSelectSession(id) {
  activeSessionId.value = id
  detailEvidence.value = null
  selectedIds.value = []
  loadEvidences()
}

async function onCreateSession(name) {
  const trimmed = String(name || '').trim()
  if (!trimmed) return
  try {
    await api('/vault/sessions', { method: 'POST', body: JSON.stringify({ name: trimmed }) })
    await loadSessions()
    showToast({ type: 'success', message: '案卷组已创建', duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '创建失败', duration: 3000 })
  }
}

async function onSelectEvidence(item) {
  try {
    detailEvidence.value = await api(`/vault/evidences/${item.id}`)
  } catch (e) {
    console.warn('load detail failed', e)
    showToast({ type: 'error', message: '证据详情加载失败', duration: 3000 })
  }
}

function onToggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function clearSelection() {
  selectedIds.value = []
}

function openConfirm(title, message, action) {
  confirmDialog.title = title
  confirmDialog.message = message
  confirmDialog.action = action
  confirmDialog.open = true
}

function closeConfirm() {
  confirmDialog.open = false
  confirmDialog.action = null
}

async function runConfirm() {
  const action = confirmDialog.action
  closeConfirm()
  if (action) await action()
}

function requestBatchDelete() {
  openConfirm(
    '删除选中证据',
    `确认永久删除 ${selectedIds.value.length} 条证据？此操作不可撤销。`,
    batchDelete,
  )
}

async function batchDelete() {
  try {
    await api('/vault/evidences/batch-delete', { method: 'POST', body: JSON.stringify({ evidence_ids: selectedIds.value }) })
    clearSelection()
    detailEvidence.value = null
    await loadEvidences()
    await loadSessions()
    showToast({ type: 'success', message: '已删除', duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '删除失败', duration: 3000 })
  }
}

async function batchExport(format = 'md') {
  const ids = selectedIds.value.length ? selectedIds.value : (detailEvidence.value ? [detailEvidence.value.id] : [])
  if (!ids.length) return
  try {
    const records = await Promise.all(ids.map(id => api(`/vault/evidences/${id}`)))
    const body = records.map(formatEvidenceMarkdown).join('\n\n---\n\n')
    downloadBlob(body, `vonish-vault-${Date.now()}.${format === 'txt' ? 'txt' : 'md'}`, format === 'txt' ? 'text/plain;charset=utf-8' : 'text/markdown;charset=utf-8')
    showToast({ type: 'success', message: `已导出 ${records.length} 条证据`, duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '导出失败', duration: 3000 })
  }
}

function requestSingleDelete() {
  if (!detailEvidence.value) return
  openConfirm('删除证据', `确认删除「${detailEvidence.value.filename}」？`, deleteSingle)
}

async function deleteSingle() {
  if (!detailEvidence.value) return
  try {
    await api(`/vault/evidences/${detailEvidence.value.id}`, { method: 'DELETE' })
    detailEvidence.value = null
    await loadEvidences()
    await loadSessions()
    showToast({ type: 'success', message: '已删除', duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '删除失败', duration: 3000 })
  }
}

function openMoveDialog() {
  const hasTarget = selectedIds.value.length || detailEvidence.value?.id
  if (!hasTarget) return
  moveTargetId.value = null
  showMoveDialog.value = true
}

async function confirmMove() {
  const ids = selectedIds.value.length ? selectedIds.value : [detailEvidence.value?.id].filter(Boolean)
  if (!ids.length) return
  try {
    await api('/vault/evidences/move-to-session', {
      method: 'POST',
      body: JSON.stringify({ evidence_ids: ids, session_id: moveTargetId.value }),
    })
    showMoveDialog.value = false
    clearSelection()
    detailEvidence.value = null
    await loadSessions()
    await loadEvidences()
    showToast({ type: 'success', message: '已移动', duration: 2000 })
  } catch (e) {
    showToast({ type: 'error', message: '移动失败', duration: 3000 })
  }
}

async function exportSingle(format = 'md') {
  await batchExport(format)
}

function onReprocess() {
  showToast({ type: 'info', message: '重新识别将加入后续队列', duration: 2000 })
}

function formatEvidenceMarkdown(ev) {
  return [
    `# ${ev.filename || '未命名证据'}`,
    '',
    `- 状态：${ev.status || '--'}`,
    `- 场景：${ev.scene_type || '--'}`,
    `- 模型：${ev.model_tier || '--'}`,
    `- 置信度：${ev.ocr_confidence != null ? `${(ev.ocr_confidence * 100).toFixed(1)}%` : '--'}`,
    '',
    '## 原始 OCR',
    '',
    ev.raw_text || '（无内容）',
    '',
    '## AI 精修',
    '',
    ev.refined_text || '（无精修结果）',
    '',
    '## Diff',
    '',
    ev.diff_json || '（无差异记录）',
  ].join('\n')
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

.vault-grid:not(:has(.vault-detail)) { grid-template-columns: 240px minmax(0, 1fr); }

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

.console-dialog-backdrop {
  position: fixed; inset: 0; z-index: 100;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--v-bg) 78%, transparent);
}

.console-dialog {
  width: min(460px, calc(100vw - 48px));
  background: var(--v-rail);
  border: 1px solid var(--v-border-strong);
  border-radius: var(--r4);
  padding: var(--s5);
}

.console-dialog-title { font-size: var(--fs-h2); margin-bottom: var(--s3); }
.confirm-copy { color: var(--v-text-muted); line-height: 1.7; margin: 0; }
.console-dialog-actions { display: flex; justify-content: flex-end; gap: var(--s3); margin-top: var(--s5); }

.secondary-btn, .primary-btn, .danger-btn {
  min-height: 34px; padding-inline: var(--s3);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: transparent;
  color: var(--v-text-muted);
  cursor: pointer;
}

.primary-btn { background: var(--v-accent); border-color: var(--v-accent); color: var(--v-coal); }
.danger-btn { background: var(--v-error); border-color: var(--v-error); color: var(--v-paper); }

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
