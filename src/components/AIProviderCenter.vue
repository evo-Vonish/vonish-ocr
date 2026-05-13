<template>
  <section class="ai-center" :class="{ wide: layout === 'wide' }">
    <div v-if="mode === 'list'" class="center-grid">
      <aside v-if="layout !== 'wide'" class="center-rail">
        <div class="section-kicker">AI FAILOVER</div>
        <h3 class="center-title">{{ titleText }}</h3>
        <p class="center-copy">
          {{ helpText }}
        </p>
        <button type="button" class="primary-action" @click="startCreate">
          + {{ createText }}
        </button>
      </aside>

      <main class="scheme-board" :class="{ full: layout === 'wide' }">
        <div class="board-head">
          <span class="section-kicker">SAVED SCHEMES</span>
          <span class="scheme-count">{{ schemes.length.toString().padStart(2, '0') }}</span>
        </div>

        <div v-if="schemes.length" class="scheme-list">
          <article
            v-for="scheme in schemes"
            :key="scheme.id"
            class="scheme-card"
            :class="{ active: scheme.id === activeId }"
          >
            <button type="button" class="scheme-main" @click="activate(scheme.id)">
              <span class="provider-mark">{{ providerShort(scheme.provider_type) }}</span>
              <span class="scheme-copy">
                <span class="scheme-name">{{ scheme.name || providerName(scheme.provider_type) }}</span>
                <span class="scheme-meta">
                  {{ providerName(scheme.provider_type) }} / {{ scheme.model || noModelText }} / W{{ scheme.weight || 1 }}
                </span>
              </span>
              <span class="scheme-state" :class="{ saved: scheme.key_saved }">
                {{ scheme.id === activeId ? activeText : scheme.key_saved ? keySavedText : keyMissingText }}
              </span>
            </button>
            <button type="button" class="edit-action" @click="startEdit(scheme)">
              {{ editText }}
            </button>
          </article>
        </div>

        <button v-else type="button" class="empty-provider" @click="startCreate">
          <span class="provider-mark">AI</span>
          <span>
            <strong>{{ emptyTitle }}</strong>
            <small>{{ emptyCopy }}</small>
          </span>
        </button>
      </main>
    </div>

    <form v-else class="editor-panel" @submit.prevent="submit">
      <header class="editor-head">
        <button type="button" class="back-action" @click="mode = 'list'">← {{ backText }}</button>
        <div>
          <div class="section-kicker">SCHEME EDITOR</div>
          <h3 class="center-title">{{ draft.id && !isNew ? editTitle : createTitle }}</h3>
        </div>
      </header>

      <div class="editor-grid">
        <label>
          <span>{{ nameLabel }}</span>
          <input v-model.trim="draft.name" type="text" :placeholder="namePlaceholder" />
        </label>
        <label>
          <span>{{ providerLabel }}</span>
          <input v-model.trim="draft.provider_type" list="provider-types" type="text" @change="applyProviderDefault" />
          <datalist id="provider-types">
            <option value="DeepSeek" />
            <option value="ChatGPT" />
            <option value="Claude" />
            <option value="Gemini" />
            <option value="Qwen" />
            <option value="Doubao" />
            <option value="豆包" />
          </datalist>
        </label>
        <label>
          <span>API Key</span>
          <input v-model.trim="draft.api_key" type="password" :placeholder="keyPlaceholder" :disabled="editingKeyLoading" />
        </label>
        <label>
          <span>Base URL</span>
          <input v-model.trim="draft.api_base" type="text" :placeholder="basePlaceholder" />
        </label>
        <label>
          <span>{{ modelLabel }}</span>
          <input v-model.trim="draft.model" type="text" placeholder="deepseek-chat / gpt-4o / claude-3-sonnet" />
        </label>
        <label>
          <span>{{ weightLabel }}</span>
          <input v-model.number="draft.weight" type="number" min="1" max="10" />
        </label>
      </div>

      <p class="hint-text">{{ failoverHint }}</p>

      <footer class="editor-actions">
        <button type="button" class="ghost-btn" @click="mode = 'list'">{{ cancelText }}</button>
        <button type="submit" class="save-scheme">{{ saveText }}</button>
      </footer>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { showToast } from '../composables/useToast'
import { currentLang } from '../i18n'

defineProps({
  layout: {
    type: String,
    default: 'compact',
  },
})

const configStore = useConfigStore()
const mode = ref('list')
const isNew = ref(true)
const editingKeyLoading = ref(false)
const draft = reactive(createDraft())

const schemes = computed(() => configStore.aiSchemes)
const activeId = computed(() => configStore.activeAiSchemeId)
const isZh = computed(() => currentLang.value === 'zh')

const copy = computed(() => isZh.value ? {
  title: 'API 方案中心',
  help: '左侧只负责说明和创建，右侧只负责切换已保存方案。创建和编辑会进入独立编辑页，避免把 Key 表单塞进切换列表。',
  create: '创建方案',
  noModel: '未指定模型',
  active: '当前',
  keySaved: 'KEY 已保存',
  keyMissing: '未保存 KEY',
  edit: '编辑',
  emptyTitle: '尚未保存 API 方案',
  emptyCopy: '创建第一个方案后即可用于 AI 精修和故障切换。',
  back: '返回列表',
  createTitle: '创建 API 方案',
  editTitle: '编辑 API 方案',
  name: '方案名称',
  namePlaceholder: '公司内网 Claude',
  provider: '厂商类型',
  keyPlaceholder: '只传给后端加密保存，不写入 localStorage',
  basePlaceholder: '可选，留空使用厂商官方 Endpoint',
  model: '模型名',
  weight: '优先级权重',
  failover: '故障切换会优先尝试当前方案；遇到 404 / 429 / 5xx / 30 秒超时后延迟 500ms，按权重尝试下一家。',
  cancel: '取消',
  save: '保存方案',
  saved: 'AI 方案已保存',
  saveFailed: 'AI 方案保存失败',
  switched: 'AI 方案已切换',
  switchFailed: 'AI 方案切换失败',
} : {
  title: 'API Provider Center',
  help: 'The left rail explains and creates. The right board only switches saved schemes. Create and edit open a dedicated editor page.',
  create: 'Create Scheme',
  noModel: 'No model',
  active: 'ACTIVE',
  keySaved: 'KEY SAVED',
  keyMissing: 'NO KEY',
  edit: 'EDIT',
  emptyTitle: 'No API scheme saved',
  emptyCopy: 'Create the first scheme for AI proofing and failover.',
  back: 'Back to list',
  createTitle: 'Create API Scheme',
  editTitle: 'Edit API Scheme',
  name: 'Scheme Name',
  namePlaceholder: 'Internal Claude',
  provider: 'Provider Type',
  keyPlaceholder: 'Encrypted by backend; never stored in localStorage',
  basePlaceholder: 'Optional. Empty means official endpoint.',
  model: 'Model Name',
  weight: 'Priority Weight',
  failover: 'Failover tries the active scheme first. On 404 / 429 / 5xx / 30s timeout, it waits 500ms and tries the next weighted provider.',
  cancel: 'Cancel',
  save: 'Save Scheme',
  saved: 'AI scheme saved',
  saveFailed: 'AI scheme save failed',
  switched: 'AI scheme switched',
  switchFailed: 'AI scheme switch failed',
})

const titleText = computed(() => copy.value.title)
const helpText = computed(() => copy.value.help)
const createText = computed(() => copy.value.create)
const noModelText = computed(() => copy.value.noModel)
const activeText = computed(() => copy.value.active)
const keySavedText = computed(() => copy.value.keySaved)
const keyMissingText = computed(() => copy.value.keyMissing)
const editText = computed(() => copy.value.edit)
const emptyTitle = computed(() => copy.value.emptyTitle)
const emptyCopy = computed(() => copy.value.emptyCopy)
const backText = computed(() => copy.value.back)
const createTitle = computed(() => copy.value.createTitle)
const editTitle = computed(() => copy.value.editTitle)
const nameLabel = computed(() => copy.value.name)
const namePlaceholder = computed(() => copy.value.namePlaceholder)
const providerLabel = computed(() => copy.value.provider)
const keyPlaceholder = computed(() => {
  if (editingKeyLoading.value) return isZh.value ? '正在读取已保存 Key...' : 'Loading saved key...'
  if (!isNew.value && draft.api_key) return isZh.value ? '已加载已保存 Key，可直接修改' : 'Saved key loaded; edit if needed'
  if (!isNew.value) return isZh.value ? '留空保存会继续沿用旧 Key' : 'Leave empty to keep the saved key'
  return copy.value.keyPlaceholder
})
const basePlaceholder = computed(() => copy.value.basePlaceholder)
const modelLabel = computed(() => copy.value.model)
const weightLabel = computed(() => copy.value.weight)
const failoverHint = computed(() => copy.value.failover)
const cancelText = computed(() => copy.value.cancel)
const saveText = computed(() => copy.value.save)

function createDraft() {
  return {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
    name: '',
    provider_type: 'DeepSeek',
    api_key: 'sk-bd11b3950f284ee0b15f05398ae31eba',
    api_base: '',
    model: 'deepseek-chat',
    weight: 5,
    enabled: true,
  }
}

onMounted(() => {
  configStore.loadAISchemes().catch(e => console.warn('加载 AI 方案失败', e))
})

function startCreate() {
  Object.assign(draft, createDraft())
  isNew.value = true
  mode.value = 'editor'
}

async function startEdit(scheme) {
  // 先清空全部字段再赋值，防止旧字段残留
  const fresh = createDraft()
  Object.assign(draft, fresh, {
    id: scheme.id,
    name: scheme.name || '',
    provider_type: providerName(scheme.provider_type),
    api_key: '',
    api_base: scheme.api_base || '',
    model: scheme.model || '',
    weight: scheme.weight || 5,
    enabled: scheme.enabled !== false,
  })
  isNew.value = false
  mode.value = 'editor'
  editingKeyLoading.value = true
  try {
    const detail = await configStore.loadAIScheme(scheme.id, { includeKey: true })
    Object.assign(draft, {
      id: detail.id,
      name: detail.name || '',
      provider_type: providerName(detail.provider_type),
      api_key: detail.api_key || '',
      api_base: detail.api_base || '',
      model: detail.model || '',
      weight: detail.weight || 5,
      enabled: detail.enabled !== false,
    })
  } catch (e) {
    showToast({ type: 'error', message: isZh.value ? '读取已保存 Key 失败，保存时将保留旧 Key' : 'Failed to load saved key. Saving will keep the old key.', duration: 4000 })
  } finally {
    editingKeyLoading.value = false
  }
}

function normalizeProvider(value) {
  const lower = String(value || '').trim().toLowerCase()
  if (lower === '豆包' || lower === 'doubao') return 'doubao'
  if (lower === 'chatgpt') return 'openai'
  return lower || 'deepseek'
}

function applyProviderDefault() {
  const provider = normalizeProvider(draft.provider_type)
  const defaults = {
    deepseek: { model: 'deepseek-chat', key: 'sk-bd11b3950f284ee0b15f05398ae31eba' },
    openai: { model: 'gpt-4o', key: '' },
    claude: { model: 'claude-3-sonnet', key: '' },
    gemini: { model: 'gemini-1.5-pro', key: '' },
    qwen: { model: 'qwen-plus', key: '' },
    doubao: { model: 'doubao-pro-32k', key: '' },
  }
  draft.provider_type = provider
  draft.model = defaults[provider]?.model || draft.model
  draft.api_key = defaults[provider]?.key || ''
}

async function submit() {
  try {
    const payload = {
      ...draft,
      provider_type: normalizeProvider(draft.provider_type),
      weight: Math.min(10, Math.max(1, Number(draft.weight) || 1)),
    }
    // 中文注释：API Key 不进入 localStorage，只随本次请求交给后端加密存储。
    await configStore.upsertAIScheme(payload)
    mode.value = 'list'
    showToast({ type: 'success', message: copy.value.saved, duration: 2200 })
  } catch (e) {
    showToast({ type: 'error', message: e?.message || copy.value.saveFailed, duration: 4000 })
  }
}

async function activate(id) {
  if (id === activeId.value) return
  try {
    await configStore.activateAIScheme(id)
    showToast({ type: 'success', message: copy.value.switched, duration: 1800 })
  } catch (e) {
    showToast({ type: 'error', message: e?.message || copy.value.switchFailed, duration: 4000 })
  }
}

function providerName(type) {
  const map = { deepseek: 'DeepSeek', openai: 'ChatGPT', claude: 'Claude', gemini: 'Gemini', qwen: 'Qwen', doubao: '豆包' }
  return map[normalizeProvider(type)] || type || 'Custom'
}

function providerShort(type) {
  return providerName(type).slice(0, 2).toUpperCase()
}

defineExpose({ startCreate })
</script>

<style scoped>
.ai-center {
  min-height: 560px;
}

.center-grid {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: var(--s5);
}

.wide .center-grid {
  grid-template-columns: 1fr;
}

.center-rail,
.scheme-board,
.editor-panel {
  background: var(--v-panel);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r4);
}

.center-rail {
  display: flex;
  flex-direction: column;
  gap: var(--s4);
  padding: var(--s5);
}

.scheme-board {
  min-width: 0;
  padding: var(--s5);
}

.section-kicker,
.scheme-meta,
.scheme-state,
.hint-text {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  letter-spacing: 0.04em;
}

.center-title {
  margin: 0;
  font-family: var(--font-title);
  font-size: var(--fs-h1);
  color: var(--v-text);
}

.center-copy {
  margin: 0;
  color: var(--v-text-muted);
  font-size: var(--fs-small);
  line-height: 1.7;
}

.primary-action,
.save-scheme {
  min-height: 40px;
  border: 0;
  border-radius: var(--r3);
  background: var(--v-accent);
  color: var(--v-coal);
  font-weight: var(--fw-semibold);
  cursor: pointer;
}

.board-head,
.editor-head,
.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
}

.board-head {
  margin-bottom: var(--s4);
}

.scheme-count {
  font-family: var(--font-mono);
  color: var(--v-accent);
}

.scheme-list {
  display: grid;
  gap: var(--s3);
}

.scheme-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: stretch;
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  overflow: hidden;
}

.scheme-card.active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.scheme-main {
  min-width: 0;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--s3);
  padding: var(--s3);
  background: transparent;
  border: 0;
  color: var(--v-text);
  text-align: left;
  cursor: pointer;
}

.provider-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: var(--v-border-width) solid var(--v-border-strong);
  border-radius: var(--r2);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-accent);
}

.scheme-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--s1);
}

.scheme-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--fs-body);
  font-weight: var(--fw-semibold);
}

.scheme-state.saved,
.scheme-card.active .scheme-state {
  color: var(--v-accent);
}

.edit-action,
.back-action,
.ghost-btn,
.empty-provider {
  background: transparent;
  color: var(--v-text-muted);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  cursor: pointer;
}

.edit-action {
  border-width: 0;
  border-left: var(--v-border-width) solid var(--v-border);
  border-radius: 0;
  padding: 0 var(--s4);
  font-family: var(--font-mono);
}

.edit-action:hover,
.back-action:hover,
.ghost-btn:hover,
.empty-provider:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
}

.empty-provider {
  width: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  gap: var(--s3);
  padding: var(--s5);
  text-align: left;
}

.empty-provider strong,
.empty-provider small {
  display: block;
}

.empty-provider small {
  margin-top: var(--s1);
  color: var(--v-text-muted);
}

.editor-panel {
  padding: var(--s5);
}

.back-action,
.ghost-btn {
  min-height: 36px;
  padding: 0 var(--s3);
}

.editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s4);
  margin-top: var(--s5);
}

.editor-grid label {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  color: var(--v-text-muted);
  font-size: var(--fs-small);
}

.editor-grid input {
  min-height: 38px;
  padding: 0 var(--s3);
  background: var(--v-bg);
  border: var(--v-border-width) solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text);
  font-family: var(--font-body);
}

.hint-text {
  margin: var(--s5) 0 0;
  line-height: 1.6;
}

.editor-actions {
  justify-content: flex-end;
  margin-top: var(--s5);
}

.editor-actions button {
  min-width: 140px;
}

@media (max-width: 760px) {
  .center-grid,
  .editor-grid {
    grid-template-columns: 1fr;
  }

  .scheme-main {
    grid-template-columns: 38px minmax(0, 1fr);
  }

  .scheme-state {
    grid-column: 2;
  }
}

</style>
