<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="lang-overlay" @click.self="close">
        <section class="lang-modal" role="dialog" aria-modal="true" :aria-label="t('langpack_title')">
          <header class="lang-head">
            <div>
              <div class="section-kicker">LANGUAGE PACKS</div>
              <h2 class="lang-title v-title">{{ t('langpack_title') }}</h2>
            </div>
            <button class="close-btn" type="button" :title="t('btn_close')" @click="close">
              <span aria-hidden="true"></span>
            </button>
          </header>

          <div class="lang-body">
            <aside class="lang-rail">
              <div class="section-kicker">{{ t('langpack_registry') }}</div>
              <p>{{ t('langpack_help') }}</p>
              <div class="rail-actions">
                <button class="ghost-action" type="button" :disabled="loading" @click="load">{{ t('langpack_refresh') }}</button>
                <button class="ghost-action" type="button" :disabled="busy" @click="verifyAll">{{ t('langpack_verify_all') }}</button>
              </div>
              <div v-if="lastVerify" class="verify-box" :class="{ ok: verifyOk, bad: !verifyOk }">
                <span>{{ verifyOk ? t('langpack_verify_ok') : t('langpack_verify_failed') }}</span>
                <small>{{ lastVerifySummary }}</small>
              </div>
            </aside>

            <main class="lang-board">
              <div class="board-head">
                <div>
                  <span class="section-kicker">{{ t('langpack_available') }}</span>
                  <input v-model.trim="query" class="search-input" type="search" :placeholder="t('langpack_search')" />
                </div>
                <span class="pack-count">{{ filteredItems.length.toString().padStart(3, '0') }} / {{ items.length }}</span>
              </div>

              <div v-if="loading" class="loading-panel">{{ t('langpack_loading') }}</div>
              <div v-else-if="!filteredItems.length" class="loading-panel">{{ t('langpack_select_hint') }}</div>
              <div v-else class="pack-grid" role="listbox" :aria-label="t('langpack_available')">
                <button
                  v-for="pack in filteredItems"
                  :key="packSpec(pack)"
                  class="pack-row"
                  :class="{ active: selected && packSpec(selected) === packSpec(pack), installed: pack.installed === 'yes' }"
                  type="button"
                  role="option"
                  :aria-selected="selected && packSpec(selected) === packSpec(pack)"
                  @click="select(pack)"
                >
                    <span class="pack-code">{{ pack.name }}</span>
                    <span class="pack-copy">
                      <strong>{{ pack.language }}</strong>
                      <small>{{ pack.model_family }} · {{ pack.quality }} · {{ pack.size_mb }} MB</small>
                    </span>
                    <span class="pack-state">{{ pack.installed === 'yes' ? t('langpack_installed') : t('langpack_not_installed') }}</span>
                </button>
              </div>
            </main>

            <aside class="detail-panel">
              <div class="section-kicker">{{ t('langpack_manifest') }}</div>
              <template v-if="detail">
                <h3>{{ detail.manifest.language.name }}</h3>
                <div class="detail-meta mono">
                  {{ detail.manifest.model_family }} / {{ detail.manifest.pack_version }} / {{ detail.manifest.quality_tier }}
                </div>
                <div class="install-path">
                  <span>{{ t('langpack_install_path') }}</span>
                  <code>{{ detail.installed?.install_dir || t('langpack_not_installed') }}</code>
                </div>
                <div class="file-list">
                  <div v-for="file in detail.manifest.files" :key="file.filename" class="file-row">
                    <span>{{ file.role }}</span>
                    <strong>{{ file.filename }}</strong>
                    <small>{{ sizeMb(file.size_bytes) }} MB</small>
                  </div>
                </div>
                <button class="primary-action" type="button" :disabled="busy || !selected" @click="installSmart()">
                  {{ selected ? installLabel(selected) : t('langpack_install_remote') }}
                </button>
                <div class="detail-actions">
                  <button class="ghost-action" type="button" :disabled="busy || selected?.installed !== 'yes'" @click="verifyOne()">
                    {{ t('langpack_verify') }}
                  </button>
                  <button class="ghost-action danger" type="button" :disabled="busy || selected?.installed !== 'yes'" @click="remove()">
                    {{ t('langpack_remove') }}
                  </button>
                </div>
                <p class="hint-text">{{ t('langpack_remote_hint') }}</p>
              </template>
              <template v-else>
                <div class="empty-detail">{{ t('langpack_select_hint') }}</div>
              </template>
            </aside>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  getLangPack,
  getLangPacks,
  pullLangPack,
  removeLangPack,
  verifyLangPacks,
} from '../api/tauri_ipc'
import { showToast } from '../composables/useToast'
import { parseApiError } from '../api/tauri_ipc'
import { t } from '../i18n'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])

const items = ref([])
const selected = ref(null)
const detail = ref(null)
const loading = ref(false)
const busy = ref(false)
const lastVerify = ref(null)
const query = ref('')

const filteredItems = computed(() => {
  const q = query.value.toLowerCase()
  if (!q) return items.value
  return items.value.filter(item => {
    return [item.name, item.language, item.model_family, item.quality]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(q))
  })
})

const verifyOk = computed(() => {
  const result = Array.isArray(lastVerify.value) ? lastVerify.value : [lastVerify.value].filter(Boolean)
  return result.length > 0 && result.every(item => item.ok)
})

const lastVerifySummary = computed(() => {
  const result = Array.isArray(lastVerify.value) ? lastVerify.value : [lastVerify.value].filter(Boolean)
  if (!result.length) return '--'
  return result.map(item => `${item.language}:${item.ok ? 'OK' : 'FAIL'}`).join(' / ')
})

watch(() => props.visible, (visible) => {
  if (visible) load()
})

function close() {
  emit('update:visible', false)
}

async function load() {
  loading.value = true
  try {
    const data = await getLangPacks()
    items.value = data.items || []
    if (!selected.value && items.value.length) {
      await select(items.value[0])
    } else if (selected.value) {
      await select(items.value.find(item => packSpec(item) === packSpec(selected.value)) || items.value[0])
    }
  } catch (e) {
    toastError(e, t('langpack_load_failed'))
  } finally {
    loading.value = false
  }
}

async function select(pack) {
  if (!pack) return
  selected.value = pack
  try {
    detail.value = await getLangPack(packSpec(pack))
  } catch (e) {
    detail.value = null
    toastError(e, t('langpack_load_failed'))
  }
}

async function installLocal(pack = selected.value) {
  pack = normalizePackArg(pack)
  if (!pack) return
  busy.value = true
  try {
    await pullLangPack(packSpec(pack), { offline: true })
    showToast({ type: 'success', message: t('langpack_install_done'), duration: 2400 })
    await load()
  } catch (e) {
    toastError(e, t('langpack_install_failed'))
  } finally {
    busy.value = false
  }
}

async function installSmart(pack = selected.value) {
  pack = normalizePackArg(pack)
  if (!pack) return
  if (pack.local_available) {
    await installLocal(pack)
  } else {
    await installRemote(pack)
  }
}

async function installRemote(pack = selected.value) {
  pack = normalizePackArg(pack)
  if (!pack) return
  busy.value = true
  try {
    await pullLangPack(packSpec(pack), { yes: true })
    showToast({ type: 'success', message: t('langpack_install_done'), duration: 2400 })
    await load()
  } catch (e) {
    toastError(e, t('langpack_install_failed'))
  } finally {
    busy.value = false
  }
}

function installLabel(pack) {
  if (pack.installed === 'yes' && pack.local_available) return t('langpack_reinstall')
  if (pack.local_available) return t('langpack_install_local')
  return t('langpack_install_remote')
}

function normalizePackArg(pack) {
  if (!pack || pack instanceof Event || !pack.name) return selected.value
  return pack
}

function packSpec(pack) {
  if (!pack) return ''
  return `${pack.model_family || 'pp-ocrv5'}:${pack.name}`
}

async function verifyOne(pack = selected.value) {
  if (!pack) return
  busy.value = true
  try {
    const data = await verifyLangPacks({ language: packSpec(pack) })
    lastVerify.value = data.result
    showToast({ type: verifyOk.value ? 'success' : 'error', message: verifyOk.value ? t('langpack_verify_ok') : t('langpack_verify_failed'), duration: 2400 })
  } catch (e) {
    toastError(e, t('langpack_verify_failed'))
  } finally {
    busy.value = false
  }
}

async function verifyAll() {
  busy.value = true
  try {
    const data = await verifyLangPacks()
    lastVerify.value = data.result
    showToast({ type: verifyOk.value ? 'success' : 'error', message: verifyOk.value ? t('langpack_verify_ok') : t('langpack_verify_failed'), duration: 2400 })
  } catch (e) {
    toastError(e, t('langpack_verify_failed'))
  } finally {
    busy.value = false
  }
}

async function remove(pack = selected.value) {
  if (!pack) return
  busy.value = true
  try {
    await removeLangPack(packSpec(pack))
    showToast({ type: 'success', message: t('langpack_remove_done'), duration: 2200 })
    await load()
  } catch (e) {
    toastError(e, t('langpack_remove_failed'))
  } finally {
    busy.value = false
  }
}

function sizeMb(size) {
  return (Number(size || 0) / (1024 * 1024)).toFixed(2)
}

function toastError(error, fallback) {
  const parsed = parseApiError(error, fallback)
  const isMissingRoute = parsed.message === 'Not Found' || parsed.message === 'Not Found.'
  showToast({
    type: 'error',
    message: isMissingRoute ? t('langpack_route_missing') : parsed.message || fallback,
    duration: 5200,
  })
}
</script>

<style scoped>
.lang-overlay {
  position: fixed;
  inset: 0;
  z-index: 1120;
  display: grid;
  place-items: center;
  padding: var(--s6);
  background: rgba(17, 17, 15, 0.78);
}

.lang-modal {
  width: min(1440px, calc(100vw - 32px));
  max-height: min(900px, calc(100vh - 32px));
  display: flex;
  flex-direction: column;
  background: var(--v-rail);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r4);
  color: var(--v-text);
  overflow: hidden;
}

.lang-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--s4);
  padding: var(--s5);
  border-bottom: var(--v-border-width) solid var(--v-border);
}

.section-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.lang-title {
  margin-top: var(--s1);
  font-size: var(--fs-h1);
}

.lang-body {
  display: grid;
  grid-template-columns: 260px minmax(0, 1.25fr) 360px;
  gap: var(--s4);
  padding: var(--s5);
  overflow: auto;
}

.lang-rail,
.lang-board,
.detail-panel {
  background: var(--v-panel);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r4);
}

.lang-rail,
.detail-panel {
  padding: var(--s4);
}

.lang-rail p,
.hint-text,
.empty-detail {
  color: var(--v-text-muted);
  font-size: var(--fs-small);
  line-height: 1.7;
}

.rail-actions {
  display: grid;
  gap: var(--s2);
  margin-top: var(--s4);
}

.ghost-action,
.primary-action {
  min-height: 36px;
  border-radius: var(--r3);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  cursor: pointer;
}

.ghost-action {
  background: transparent;
  color: var(--v-text-muted);
  border: var(--v-border-width) solid var(--v-border);
}

.primary-action {
  width: 100%;
  margin-top: var(--s4);
  background: var(--v-accent);
  color: var(--v-coal);
  border: 0;
  font-weight: var(--fw-semibold);
}

.ghost-action:hover,
.v-state-tab:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
}

.board-head {
  min-height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-inline: var(--s4);
  border-bottom: var(--v-border-width) solid var(--v-border);
}

.board-head > div {
  display: grid;
  gap: var(--s2);
}

.search-input {
  width: min(420px, 52vw);
  height: 32px;
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
  color: var(--v-text);
  padding-inline: var(--s3);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  outline: none;
}

.search-input:focus {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.pack-count {
  font-family: var(--font-mono);
  color: var(--v-accent);
}

.pack-grid {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
  padding: var(--s4);
  max-height: min(680px, calc(100vh - 220px));
  overflow: auto;
}

.pack-row {
  width: 100%;
  min-height: 58px;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--s3);
  padding: var(--s3);
  background: var(--v-rail);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text);
  text-align: left;
  cursor: pointer;
}

.pack-row.active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.pack-row.installed .pack-code {
  border-color: var(--v-accent);
}

.pack-code {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r2);
  font-family: var(--font-mono);
  color: var(--v-accent);
  text-transform: uppercase;
}

.pack-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.pack-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pack-copy small,
.pack-state,
.detail-meta,
.file-row small,
.install-path span {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.pack-state {
  color: var(--v-accent);
}

.detail-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s2);
  margin-top: var(--s2);
}

.pack-badges {
  display: inline-flex;
  align-items: center;
  gap: var(--s2);
  justify-content: end;
}

.pack-badge {
  padding: 2px var(--s2);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
}

.ghost-action.danger {
  border-color: var(--v-error);
  color: var(--v-error);
}

.detail-panel h3 {
  margin: var(--s3) 0 var(--s1);
  font-size: var(--fs-h2);
}

.install-path {
  display: grid;
  gap: var(--s2);
  margin-top: var(--s4);
}

.install-path code {
  padding: var(--s2);
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r2);
  color: var(--v-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  overflow-wrap: anywhere;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  margin-top: var(--s4);
}

.file-row {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr) auto;
  gap: var(--s2);
  align-items: center;
  padding: var(--s2);
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r2);
}

.file-row strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.verify-box,
.loading-panel {
  margin-top: var(--s4);
  padding: var(--s3);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
  font-family: var(--font-mono);
  color: var(--v-text-muted);
}

.verify-box.ok {
  border-color: var(--v-accent);
  color: var(--v-accent);
}

.verify-box.bad {
  border-color: var(--v-error);
  color: var(--v-error);
}

.verify-box small {
  display: block;
  margin-top: var(--s1);
  color: var(--v-text-muted);
}

.close-btn {
  width: 36px;
  height: 36px;
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
  display: block;
  background: currentColor;
}

.close-btn span {
  transform: rotate(45deg);
}

.close-btn span::after {
  content: "";
  transform: rotate(90deg);
}

button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) var(--ease-cut);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 960px) {
  .lang-body {
    grid-template-columns: 1fr;
  }
}
</style>
