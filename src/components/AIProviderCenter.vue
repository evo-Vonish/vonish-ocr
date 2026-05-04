<template>
  <section class="ai-center">
    <header class="ai-head">
      <div>
        <div class="section-kicker">AI FAILOVER</div>
        <h4>API 方案中心</h4>
      </div>
      <span class="scheme-count">{{ schemes.length.toString().padStart(2, '0') }}</span>
    </header>

    <div class="scheme-list">
      <button
        v-for="scheme in schemes"
        :key="scheme.id"
        type="button"
        class="scheme-card"
        :class="{ active: scheme.id === activeId }"
        @click="activate(scheme.id)"
      >
        <span class="provider-mark">{{ providerShort(scheme.provider_type) }}</span>
        <span class="scheme-copy">
          <span class="scheme-name">{{ scheme.name || providerName(scheme.provider_type) }}</span>
          <span class="scheme-meta">
            {{ scheme.model || '未指定模型' }} · W{{ scheme.weight || 1 }}
            <span v-if="scheme.key_saved"> · KEY SAVED</span>
          </span>
        </span>
      </button>
      <button type="button" class="create-entry" @click="startCreate">+ 创建方案</button>
    </div>

    <form v-if="editing" class="scheme-form" @submit.prevent="submit">
      <label>
        方案名称
        <input v-model.trim="draft.name" type="text" placeholder="公司内网 Claude" />
      </label>
      <label>
        厂商类型
        <input v-model.trim="draft.provider_type" list="provider-types" type="text" @change="applyProviderDefault" />
        <datalist id="provider-types">
          <option value="DeepSeek" />
          <option value="ChatGPT" />
          <option value="Claude" />
          <option value="Gemini" />
          <option value="Qwen" />
          <option value="豆包" />
        </datalist>
      </label>
      <label>
        API Key
        <input v-model.trim="draft.api_key" type="password" placeholder="加密保存到本机 Key Store" />
      </label>
      <label>
        Base URL
        <input v-model.trim="draft.api_base" type="text" placeholder="可选，留空使用官方 Endpoint" />
      </label>
      <label>
        模型名
        <input v-model.trim="draft.model" type="text" placeholder="deepseek-chat / gpt-4o / claude-3-sonnet" />
      </label>
      <label>
        优先级权重
        <input v-model.number="draft.weight" type="number" min="1" max="10" />
      </label>
      <div class="form-actions">
        <button type="button" class="ghost-btn" @click="editing = false">取消</button>
        <button type="submit" class="save-scheme">保存方案</button>
      </div>
      <p class="hint-text">故障切换会按当前方案优先、其余方案按权重排序，遇到 404 / 429 / 5xx / 30 秒超时后延迟 500ms 重试下一家。</p>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { showToast } from '../composables/useToast'

const configStore = useConfigStore()
const editing = ref(false)

const schemes = computed(() => configStore.aiSchemes)
const activeId = computed(() => configStore.activeAiSchemeId)

const draft = reactive(createDraft())

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
  configStore.loadAISchemes()
})

function startCreate() {
  Object.assign(draft, createDraft())
  editing.value = true
}

function normalizeProvider(value) {
  const lower = String(value || '').trim().toLowerCase()
  if (lower === '豆包') return 'doubao'
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
    // 中文注释：API Key 不进入 localStorage，只随本次请求交给后端 DPAPI 加密存储。
    await configStore.upsertAIScheme(payload)
    editing.value = false
    showToast({ type: 'success', message: 'AI 方案已保存', duration: 2200 })
  } catch (e) {
    showToast({ type: 'error', message: e?.message || 'AI 方案保存失败', duration: 4000 })
  }
}

async function activate(id) {
  if (id === activeId.value) return
  try {
    await configStore.activateAIScheme(id)
    showToast({ type: 'success', message: 'AI 方案已切换', duration: 1800 })
  } catch (e) {
    showToast({ type: 'error', message: e?.message || 'AI 方案切换失败', duration: 4000 })
  }
}

function providerName(type) {
  const map = { deepseek: 'DeepSeek', openai: 'ChatGPT', claude: 'Claude', gemini: 'Gemini', qwen: 'Qwen', doubao: '豆包' }
  return map[normalizeProvider(type)] || type || 'Custom'
}

function providerShort(type) {
  return providerName(type).slice(0, 2).toUpperCase()
}
</script>

<style scoped>
.ai-center {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}

.ai-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s3);
}

.section-kicker,
.scheme-meta {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.scheme-count {
  font-family: var(--font-mono);
  color: var(--v-accent);
}

.scheme-list {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
}

.scheme-card,
.create-entry {
  width: 100%;
  min-height: 48px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: var(--s3);
  padding: var(--s2);
  background: var(--v-bg);
  color: var(--v-text);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  text-align: left;
  cursor: pointer;
}

.scheme-card.active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.provider-mark {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 1px solid var(--v-border-strong);
  border-radius: var(--r2);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-accent);
}

.scheme-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.scheme-name {
  font-size: var(--fs-small);
  font-weight: var(--fw-semibold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.create-entry {
  display: block;
  min-height: 36px;
  color: var(--v-text-muted);
  text-align: center;
}

.scheme-form {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
  padding-top: var(--s3);
  border-top: 1px solid var(--v-border);
}

.form-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s2);
}

.ghost-btn,
.save-scheme {
  min-height: 36px;
  border-radius: var(--r3);
  cursor: pointer;
}

.ghost-btn {
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
}

.save-scheme {
  background: var(--v-accent);
  color: var(--v-coal);
  border: 0;
  font-weight: var(--fw-semibold);
}
</style>
