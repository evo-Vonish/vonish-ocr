<template>
  <section class="backend-console">
    <header class="console-top">
      <div class="console-heading">
        <span class="breath-dot" :class="{ stopped: localApi.status !== 'running' }" aria-hidden="true"></span>
        <div>
          <h1 class="console-title v-title">机柜状态</h1>
          <div class="console-kicker">VonishOCR · LOCAL MACHINE ROOM</div>
        </div>
      </div>
      <button class="return-btn" type="button" @click="$emit('close')">← 返回证据桌</button>
    </header>

    <main class="console-main">
      <section class="metric-grid">
        <article class="metric-card gpu-card">
          <div class="metric-head">
            <span>GPU</span>
            <span class="mono faint">{{ hardware.gpu.name }}</span>
          </div>
          <div class="gpu-body">
            <div class="ring" :style="{ '--pct': gpuVramPct + '%' }"><span>{{ gpuVramPct }}%</span></div>
            <div class="metric-stack">
              <Readout label="VRAM" :value="`${hardware.gpu.vramUsed}/${hardware.gpu.vramTotal} GB`" />
              <Bar label="UTIL" :value="hardware.gpu.util" unit="%" />
              <Readout label="TEMP" :value="`${hardware.gpu.temp || '--'} C`" />
              <Readout label="POWER" :value="`${hardware.gpu.power || '--'} W`" />
              <Bar label="GPU FAN" :value="fanPct(hardware.gpu.fan)" :text="`${hardware.gpu.fan || 0} RPM`" />
            </div>
          </div>
          <div class="bus-line mono">{{ hardware.bus }}</div>
        </article>

        <article class="metric-card">
          <div class="metric-head">
            <span>CPU</span>
            <span class="mono faint">{{ hardware.cpu.name }}</span>
          </div>
          <Readout label="CORES" :value="hardware.cpu.cores" />
          <Bar label="UTIL" :value="hardware.cpu.util" unit="%" />
          <Readout label="FREQ" :value="`${hardware.cpu.freq || '--'} GHz`" />
          <Readout label="TEMP" :value="`${hardware.cpu.temp || '--'} C`" />
          <Bar label="CPU FAN" :value="fanPct(hardware.fanCpu)" :text="`${hardware.fanCpu || 0} RPM`" />
        </article>

        <article class="metric-card">
          <div class="metric-head">
            <span>MEMORY</span>
            <span class="mono faint">{{ hardware.mem.type }}</span>
          </div>
          <Readout label="USED" :value="`${hardware.mem.used || '--'}/${hardware.mem.total || '--'} GB`" />
          <Bar label="LOAD" :value="memPct" unit="%" />
        </article>

        <article class="metric-card">
          <div class="metric-head">
            <span>DISK</span>
            <span class="mono faint">CACHE</span>
          </div>
          <Readout label="MODEL CACHE" :value="`${hardware.disk.cacheSize} GB`" />
          <Bar label="FREE" :value="diskFreePct" :text="`${hardware.disk.free} GB`" />
          <button class="secondary-btn" type="button" :disabled="busyAction === 'cache'" @click="clearCache">
            {{ busyAction === 'cache' ? '清理中' : '清理缓存' }}
          </button>
        </article>
      </section>

      <section class="console-grid">
        <article class="console-panel">
          <div class="panel-title">模型驻留与三档</div>
          <div class="resident-card">
            <span class="mono accent">{{ activeModel?.name || '未加载' }}</span>
            <span class="mono">{{ activeModel?.size || '--' }} · {{ modelStatusText(activeModel?.status) }}</span>
          </div>
          <div class="button-row langpack-row">
            <button class="secondary-btn" type="button" @click="showLanguagePacks = true">{{ t('langpack_console_entry') }}</button>
            <button class="secondary-btn" type="button" @click="openModelsFolder">打开模型目录</button>
          </div>

          <div class="capsule-row">
            <button
              v-for="model in models"
              :key="model.id"
              type="button"
              class="capsule"
              :class="{ active: currentModelId === model.id, blocked: model.status === 'needs-convert', busy: modelSwitchingId === model.id }"
              :disabled="Boolean(modelSwitchingId)"
              @click="chooseModel(model)"
            >
              <span>{{ modelLabel(model.id) }}</span>
              <small>{{ model.status === 'needs-convert' ? '需 ONNX 转换 · 转换' : model.name }}</small>
            </button>
          </div>

          <ol v-if="modelSteps.length" class="step-list">
            <li v-for="step in modelSteps" :key="step.name" :class="step.status">
              <span>{{ step.name }}</span>
              <small>{{ step.detail }}</small>
            </li>
          </ol>
        </article>

        <article class="console-panel">
          <div class="panel-title">性能模式</div>
          <div class="profile-row">
            <button
              v-for="profile in profiles"
              :key="profile.id"
              type="button"
              class="profile-pill"
              :class="{ active: currentProfileId === profile.id, busy: busyAction === `profile:${profile.id}` }"
              :disabled="Boolean(busyAction)"
              @click="chooseProfile(profile)"
            >
              <span>{{ profile.name }}</span>
              <small>{{ profileSummary(profile) }}</small>
            </button>
          </div>
          <div v-if="performancePolicy" class="resident-card performance-card">
            <span class="mono">ACTIVE {{ performancePolicy.mode?.toUpperCase?.() || currentProfileId.toUpperCase() }}</span>
            <small>
              CONC {{ runtimePolicy?.current_concurrency || performancePolicy.concurrency }}
              / BATCH {{ performancePolicy.batch_size }}
              / PREP {{ performancePolicy.preprocess_workers }}
            </small>
            <small>{{ performancePolicy.reason }}</small>
          </div>
        </article>

        <article class="console-panel api-panel">
          <div class="panel-title">本地 API 管理</div>
          <div class="endpoint-row">
            <span class="mono endpoint">{{ endpoint }}</span>
            <button class="secondary-btn" type="button" @click="copyEndpoint">复制</button>
          </div>

          <div class="status-row">
            <span class="status-dot" :class="localApi.status"></span>
            <span class="mono">{{ localApi.status === 'running' ? 'RUNNING' : 'STOPPED' }}</span>
            <span class="port-edit">
              PORT
              <input
                v-if="editingPort"
                v-model="portDraft"
                class="port-input"
                @blur="commitPort"
                @keyup.enter="commitPort"
                @keyup.esc="cancelPort"
              />
              <button v-else class="port-btn mono" type="button" @click="startPortEdit">{{ localApi.port || '--' }}</button>
            </span>
          </div>

          <div class="stat-row">
            <Readout label="今日" :value="localApi.stats.today" />
            <Readout label="平均" :value="`${localApi.stats.avgMs} ms`" />
            <Readout label="错误" :value="`${(localApi.stats.errorRate * 100).toFixed(2)}%`" />
          </div>

          <div class="request-table">
            <div class="request-head"><span>METHOD</span><span>PATH</span><span>CODE</span><span>MS</span><span>TIME</span></div>
            <div v-for="req in localApi.recentRequests.slice(0, 5)" :key="`${req.time}-${req.path}`" class="request-row">
              <span>{{ req.method }}</span>
              <span>{{ req.path }}</span>
              <span :class="{ error: req.code >= 400 }">{{ req.code }}</span>
              <span>{{ req.ms }}</span>
              <span>{{ req.time }}</span>
            </div>
          </div>

          <div class="button-row">
            <button class="primary-btn" type="button" :disabled="serviceBusy || localApi.status !== 'running'" @click="runTestRequest">测试请求</button>
            <button class="secondary-btn" type="button" :disabled="serviceBusy" @click="runServiceAction('restart')">重启服务</button>
            <button v-if="localApi.status === 'running'" class="danger-btn" type="button" :disabled="serviceBusy" @click="runServiceAction('stop')">停止服务</button>
            <button v-else class="primary-btn" type="button" :disabled="serviceBusy" @click="runServiceAction('start')">启动服务</button>
            <button class="secondary-btn" type="button" @click="showExample = !showExample">{{ showExample ? '收起示例' : '展开示例' }}</button>
          </div>

          <ol v-if="serviceSteps.length" class="step-list service-steps">
            <li v-for="step in serviceSteps" :key="step.name" :class="step.status">
              <span>{{ step.name }}</span>
              <small>{{ step.detail }}</small>
            </li>
          </ol>

          <pre v-if="showExample" class="code-sample">import requests

payload = {"image": "data:image/png;base64,...", "options": {}}
res = requests.post("{{ endpoint }}", json=payload, timeout=30)
print(res.json())</pre>
        </article>

        <article class="console-panel log-panel">
          <div class="log-head">
            <div class="panel-title">实时日志流</div>
            <div class="filter-row">
              <button v-for="f in filters" :key="f.id" type="button" class="filter-pill" :class="{ active: logFilter === f.id }" @click="logFilter = f.id">{{ f.name }}</button>
            </div>
          </div>
          <div ref="logBox" class="terminal">
            <div v-for="(log, i) in filteredLogs" :key="i" class="log-line" :class="log.level">
              <span>[{{ log.t }}]</span> <span>[{{ log.tag }}]</span> <span>{{ log.msg }}</span>
            </div>
          </div>
          <div class="button-row">
            <button class="secondary-btn" type="button" @click="exportCsv">导出 CSV</button>
            <button class="danger-btn" type="button" @click="clearLogs">清空</button>
          </div>
        </article>
      </section>

      <QueueMonitor />

      <section class="queue-strip mono">
        <span>QUEUE <b>{{ queue.pending.toString().padStart(2, '0') }}</b></span>
        <span>PROC <b>{{ queue.processing.toString().padStart(2, '0') }}</b></span>
        <span>DONE <b>{{ queue.done }}</b></span>
        <span>BATCH <b>{{ queue.batchPercent }}%</b></span>
        <span>ETA <b>{{ queue.eta }}</b></span>
      </section>

      <section class="system-actions">
        <button class="secondary-btn" type="button" @click="exportDiagnostics">导出诊断包</button>
        <button class="secondary-btn" type="button" :disabled="busyAction === 'update'" @click="checkUpdates">
          {{ busyAction === 'update' ? '检查中' : '检查更新' }}
        </button>
        <button class="secondary-btn" type="button" @click="openModelsFolder">打开模型目录</button>
        <button class="secondary-btn" type="button" :disabled="busyAction === 'cache'" @click="clearCache">清理模型缓存</button>
      </section>

      <footer class="nameplate mono">
        OS {{ sysInfo.os }} · AppVer {{ sysInfo.appVer }} · Python {{ sysInfo.pyVer }} · Tauri {{ sysInfo.tauriVer }}
      </footer>
    </main>

    <div v-if="consoleDialog" class="console-dialog-backdrop" @click.self="resolveConsoleDialog(false)">
      <section class="console-dialog" role="dialog" aria-modal="true">
        <div class="console-dialog-title v-title">{{ consoleDialog.title }}</div>
        <p>{{ consoleDialog.message }}</p>
        <div class="console-dialog-actions">
          <button v-if="consoleDialog.type === 'confirm'" class="secondary-btn" type="button" @click="resolveConsoleDialog(false)">
            {{ consoleDialog.cancelText }}
          </button>
          <button class="primary-btn" type="button" @click="resolveConsoleDialog(true)">
            {{ consoleDialog.confirmText }}
          </button>
        </div>
      </section>
    </div>
    <LanguagePackModal v-model:visible="showLanguagePacks" />
  </section>
</template>

<script setup>
import { computed, defineComponent, h, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  applyConsolePerformance,
  clearConsoleCache,
  controlBackendService,
  getBackendConsoleStatus,
  getBackendServiceState,
  openModelDir,
  switchConsoleModel,
  testBackendRequest,
} from '../api/tauri_ipc'
import { useConfigStore } from '../stores/configStore'
import { useTaskStore } from '../stores/taskStore'
import { showToast } from '../composables/useToast'
import { downloadBlob } from '../utils/exporters'
import QueueMonitor from './console/QueueMonitor.vue'
import LanguagePackModal from './LanguagePackModal.vue'
import { t } from '../i18n'

defineEmits(['close'])

// 小读数单元：统一所有硬件数字的 label/value 排版，避免文本挤在一起。
const Readout = defineComponent({
  props: { label: String, value: [String, Number] },
  setup(props) {
    return () => h('div', { class: 'readout' }, [
      h('span', props.label),
      h('b', props.value),
    ])
  },
})

// 横向细条：用于 CPU/GPU/内存/风扇等百分比读数。
const Bar = defineComponent({
  props: { label: String, value: [String, Number], unit: String, text: String },
  setup(props) {
    const width = computed(() => `${Math.max(0, Math.min(100, Number(props.value) || 0))}%`)
    return () => h('div', { class: 'bar-row' }, [
      h('div', { class: 'bar-meta' }, [
        h('span', props.label),
        h('b', props.text || `${props.value}${props.unit || ''}`),
      ]),
      h('div', { class: 'thin-bar' }, [h('span', { style: { width: width.value } })]),
    ])
  },
})

const configStore = useConfigStore()
const taskStore = useTaskStore()
const logBox = ref(null)
const logFilter = ref('all')
const showExample = ref(false)
const editingPort = ref(false)
const portDraft = ref('')
const consoleDialog = ref(null)
const modelSteps = ref([])
const serviceSteps = ref([])
const modelSwitchingId = ref('')
const serviceBusy = ref(false)
const busyAction = ref('')
const showLanguagePacks = ref(false)
let refreshTimer = null

// 控制台初始数据。真实数据由 /v1/console/status 覆盖。
const hardware = ref({
  gpu: { name: 'DirectML GPU', vramTotal: 0, vramUsed: 0, util: 0, temp: 0, power: 0, fan: 0 },
  cpu: { name: 'CPU', cores: 0, util: 0, freq: 0, temp: 0 },
  mem: { type: 'SYSTEM', total: 0, used: 0 },
  disk: { cacheSize: 0, free: 0 },
  bus: 'PCIe 4.0 x16',
  fanCpu: 0,
})

const models = ref([
  { id: 'rapid', name: 'rapidocr-mobile-cn', size: '22MB', status: 'resident', active: true },
  { id: 'cnocr', name: 'cnocr-standard-cn', size: '80MB', status: 'unloaded', active: false },
  { id: 'paddle', name: 'paddleocr-vl-1.5', size: '1.87GB', status: 'needs-convert', active: false },
])
const currentModelId = ref('rapid')

const profiles = ref([
  { id: 'auto', name: '自动', policy: { concurrency: 1, batch_size: 1, preprocess_workers: 1 } },
  { id: 'beast', name: '野兽', policy: { concurrency: 2, batch_size: 2, preprocess_workers: 2 } },
  { id: 'balanced', name: '均衡', policy: { concurrency: 1, batch_size: 1, preprocess_workers: 1 } },
  { id: 'eco', name: '节能', policy: { concurrency: 1, batch_size: 1, preprocess_workers: 1 } },
])
const currentProfileId = ref('balanced')
const performancePolicy = ref(null)
const runtimePolicy = ref(null)

const localApi = ref({
  endpoint: 'http://localhost:8000/v1/ocr',
  port: 8000,
  status: 'running',
  stats: { today: 0, avgMs: 0, errorRate: 0 },
  recentRequests: [],
})
const logs = ref([])
const sysInfo = ref({ os: 'Windows', appVer: '0.1.0', pyVer: '3.x', tauriVer: '2.x' })

const queue = computed(() => ({
  pending: taskStore.pendingCount,
  processing: taskStore.processingCount,
  done: taskStore.doneCount,
  batchPercent: taskStore.tasks.length ? Math.round((taskStore.doneCount / taskStore.tasks.length) * 100) : 0,
  eta: taskStore.processingCount ? '00:02:14' : '00:00:00',
}))

const filters = [
  { id: 'all', name: '全部' },
  { id: 'OCR', name: 'OCR' },
  { id: 'MODEL', name: '模型' },
  { id: 'API', name: 'API' },
  { id: 'ERROR', name: '错误' },
]

const endpoint = computed(() => localApi.value.port ? `http://localhost:${localApi.value.port}/v1/ocr` : '服务已停止')
const activeModel = computed(() => models.value.find(m => m.id === currentModelId.value))
const gpuVramPct = computed(() => pct(hardware.value.gpu.vramUsed, hardware.value.gpu.vramTotal))
const memPct = computed(() => pct(hardware.value.mem.used, hardware.value.mem.total))
const diskFreePct = computed(() => Math.min(100, Math.round((hardware.value.disk.free / 512) * 100)))
const filteredLogs = computed(() => logs.value.filter(log => {
  if (logFilter.value === 'all') return true
  if (logFilter.value === 'ERROR') return log.level === 'error'
  return log.tag === logFilter.value
}))

onMounted(() => {
  refreshStatus()
  refreshTimer = window.setInterval(refreshStatus, 2500)
})

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})

watch(filteredLogs, async () => {
  await nextTick()
  if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
}, { flush: 'post' })

function pct(used, total) {
  const u = Number(used) || 0
  const t = Number(total) || 0
  return t > 0 ? Math.min(100, Math.round((u / t) * 100)) : 0
}

function fanPct(rpm) {
  return Math.min(100, Math.round((Number(rpm) || 0) / 40))
}

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

function appendLog(level, tag, msg) {
  logs.value = [...logs.value.slice(-119), { t: nowTime(), level, tag, msg }]
}

function setStep(listRef, name, status, detail = '') {
  const old = listRef.value.filter(step => step.name !== name)
  listRef.value = [...old, { name, status, detail }]
}

// 刷新控制台状态：先问 Tauri sidecar 是否还活着；停止状态下不再请求 HTTP。
async function refreshStatus() {
  try {
    const service = await getBackendServiceState()
    if (service.status !== 'running') {
      localApi.value = { ...localApi.value, status: 'stopped', port: 0 }
      return
    }

    const data = await getBackendConsoleStatus()
    hardware.value = { ...hardware.value, ...(data.hardware || {}) }
    models.value = data.models || models.value
    localApi.value = { ...localApi.value, ...(data.localApi || {}), status: 'running' }
    logs.value = data.logs?.length ? data.logs : logs.value.length ? logs.value : seedLogs()
    sysInfo.value = { ...sysInfo.value, ...(data.sysInfo || {}) }
    if (data.performance) {
      performancePolicy.value = data.performance.policy || performancePolicy.value
      runtimePolicy.value = data.performance.runtime || runtimePolicy.value
      profiles.value = data.performance.profiles || data.profiles || profiles.value
      currentProfileId.value = data.performance.activeMode || currentProfileId.value
    } else if (data.profiles) {
      profiles.value = data.profiles
    }
    const active = models.value.find(m => m.active)
    if (active && !modelSwitchingId.value) currentModelId.value = active.id
  } catch (e) {
    appendLog('error', 'API', `控制台状态读取失败: ${e.message || e}`)
    localApi.value = { ...localApi.value, status: 'stopped' }
  }
}

async function chooseModel(model) {
  if (model.status === 'needs-convert') {
    await openConsoleAlert({ title: '需要转换', message: '专业模型当前是 Transformers 格式，需要转换为 ONNX 后才能驻留。' })
    return
  }
  if (model.id === currentModelId.value || modelSwitchingId.value) return
  const ok = await openConsoleConfirm({
    title: '切换驻留模型',
    message: `确认卸载当前模型并加载 ${model.name}？控制台会展示后端返回的真实步骤。`,
    confirmText: '切换',
    cancelText: '取消',
  })
  if (!ok) return

  modelSwitchingId.value = model.id
  modelSteps.value = []
  setStep(modelSteps, '提交切换请求', 'current', model.name)
  appendLog('info', 'MODEL', `开始切换模型 -> ${model.name}`)

  try {
    setStep(modelSteps, '提交切换请求', 'done', '后端已接收')
    setStep(modelSteps, '卸载旧模型', 'current', '等待后端执行')
    const result = await switchConsoleModel(model.id)

    modelSteps.value = (result.steps || []).map(step => ({
      name: step.name,
      status: step.status || 'done',
      detail: step.detail || '',
    }))
    setStep(modelSteps, '完成校验', 'done', `当前驻留: ${result.active_model}`)
    currentModelId.value = model.id
    await configStore.loadConfig()
    await refreshStatus()
    appendLog('info', 'MODEL', `模型切换完成 -> ${result.active_model}`)
    showToast({ type: 'success', message: `已切换到 ${model.name}`, duration: 2200 })
  } catch (e) {
    const detail = e?.detail?.message || e?.message || String(e)
    setStep(modelSteps, '切换失败', 'error', detail)
    appendLog('error', 'MODEL', `模型切换失败: ${detail}`)
    showToast({ type: 'error', message: detail, duration: 4200 })
  } finally {
    modelSwitchingId.value = ''
  }
}

function modelLabel(id) {
  return ({ rapid: '极速', cnocr: '标准', paddle: '专业' })[id] || id
}

function modelStatusText(status) {
  return ({ resident: '驻留中', unloaded: '未加载', 'needs-convert': '需转换' })[status] || status || '--'
}

function profileSummary(profile) {
  const policy = profile.policy || profile
  const concurrency = policy.concurrency ?? profile.concurrent ?? '--'
  const batch = policy.batch_size ?? policy.batch ?? concurrency
  const prep = policy.preprocess_workers ?? '--'
  const thermal = policy.thermal_limit_c ? ` · ${policy.thermal_limit_c}C` : ''
  return `并发 ${concurrency} · 批量 ${batch} · 预处理 ${prep}${thermal}`
}

async function chooseProfile(profile) {
  if (busyAction.value || profile.id === currentProfileId.value) return
  busyAction.value = `profile:${profile.id}`
  appendLog('info', 'QUEUE', `性能模式计算 -> ${profile.name}`)
  try {
    const result = await applyConsolePerformance(profile.id)
    currentProfileId.value = result.mode || profile.id
    performancePolicy.value = result.policy || performancePolicy.value
    runtimePolicy.value = result.runtime || runtimePolicy.value
    profiles.value = result.profiles || profiles.value
    await configStore.loadConfig()
    appendLog(
      'info',
      'QUEUE',
      `性能模式已应用 -> ${profile.name} / 并发 ${performancePolicy.value?.concurrency || '--'} / 批量 ${performancePolicy.value?.batch_size || '--'}`,
    )
    showToast({ type: 'success', message: `性能模式已应用：${profile.name}`, duration: 2200 })
  } catch (e) {
    const detail = e?.detail?.message || e?.message || String(e)
    appendLog('error', 'QUEUE', `性能模式切换失败: ${detail}`)
    showToast({ type: 'error', message: detail, duration: 4200 })
  } finally {
    busyAction.value = ''
  }
}

async function copyEndpoint() {
  await navigator.clipboard.writeText(endpoint.value)
  showToast({ type: 'success', message: 'Endpoint 已复制', duration: 1800 })
}

function startPortEdit() {
  portDraft.value = String(localApi.value.port || '')
  editingPort.value = true
}

function commitPort() {
  const next = Number(portDraft.value)
  if (!Number.isInteger(next) || next < 1 || next > 65535) {
    showToast({ type: 'error', message: '端口必须是 1-65535 的整数', duration: 2600 })
  } else {
    localApi.value.port = next
    appendLog('warn', 'API', `Endpoint 显示端口临时改为 ${next}，真实 sidecar 端口由 Tauri 管理`)
  }
  editingPort.value = false
}

function cancelPort() {
  editingPort.value = false
}

async function runTestRequest() {
  try {
    await testBackendRequest()
    appendLog('api', 'API', 'GET /health 200 OK')
    showToast({ type: 'success', message: '本地 API 测试通过', duration: 2200 })
  } catch (e) {
    appendLog('error', 'API', `GET /health failed: ${e.message || e}`)
    showToast({ type: 'error', message: '本地 API 测试失败', duration: 3600 })
  }
}

async function runServiceAction(action) {
  const actionName = ({ stop: '停止服务', start: '启动服务', restart: '重启服务' })[action]
  const ok = await openConsoleConfirm({
    title: actionName,
    message: action === 'stop' ? '停止后 OCR、配置和模型接口会暂时不可用，可在本面板重新启动。' : '将由 Tauri 重新拉起 Python sidecar，并重新探测健康状态。',
    confirmText: actionName,
    cancelText: '取消',
  })
  if (!ok) return

  serviceBusy.value = true
  serviceSteps.value = []
  setStep(serviceSteps, '提交控制指令', 'current', actionName)
  appendLog('warn', 'API', `${actionName} 开始`)

  try {
    setStep(serviceSteps, '提交控制指令', 'done', 'Tauri 已接收')
    setStep(serviceSteps, action === 'stop' ? '终止 sidecar' : '重建 sidecar', 'current', '执行中')
    const state = await controlBackendService(action)
    setStep(serviceSteps, action === 'stop' ? '终止 sidecar' : '重建 sidecar', 'done', `PID ${state.pid || '--'} · PORT ${state.port || '--'}`)
    localApi.value = { ...localApi.value, status: state.status, port: state.port || 0 }

    if (state.status === 'running') {
      setStep(serviceSteps, '健康检查', 'current', '/health')
      await wait(350)
      await testBackendRequest()
      setStep(serviceSteps, '健康检查', 'done', 'HTTP 200')
      await refreshStatus()
    }
    appendLog('info', 'API', `${actionName} 完成`)
    showToast({ type: 'success', message: `${actionName}完成`, duration: 2200 })
  } catch (e) {
    const detail = e?.message || String(e)
    setStep(serviceSteps, '操作失败', 'error', detail)
    appendLog('error', 'API', `${actionName}失败: ${detail}`)
    showToast({ type: 'error', message: `${actionName}失败`, duration: 3600 })
  } finally {
    serviceBusy.value = false
  }
}

async function clearLogs() {
  const ok = await openConsoleConfirm({ title: '清空日志视图', message: '只清空当前控制台视图，不删除日志文件。', confirmText: '清空' })
  if (ok) logs.value = []
}

function exportCsv() {
  const csv = ['time,level,tag,message'].concat(logs.value.map(l => `${l.t},${l.level},${l.tag},"${String(l.msg).replaceAll('"', '""')}"`)).join('\n')
  downloadBlob(csv, 'vonish-console-logs.csv', 'text/csv;charset=utf-8')
  appendLog('info', 'API', '日志 CSV 已导出')
}

async function openModelsFolder() {
  await openModelDir()
  appendLog('info', 'MODEL', '已请求打开模型目录')
}

async function clearCache() {
  const ok = await openConsoleConfirm({ title: '清理模型缓存', message: '此操作只释放模型驻留和显存占用，不删除模型文件。继续？', confirmText: '清理' })
  if (!ok) return
  busyAction.value = 'cache'
  try {
    const result = await clearConsoleCache()
    models.value = models.value.map(model => ({ ...model, active: false, status: model.status === 'needs-convert' ? model.status : 'unloaded' }))
    appendLog('info', 'MODEL', result.message || '模型驻留缓存已释放')
    showToast({ type: 'success', message: '模型驻留缓存已释放', duration: 2200 })
    await refreshStatus()
  } catch (e) {
    appendLog('error', 'MODEL', `缓存清理失败: ${e.message || e}`)
    showToast({ type: 'error', message: '缓存清理失败', duration: 3600 })
  } finally {
    busyAction.value = ''
  }
}

async function checkUpdates() {
  busyAction.value = 'update'
  try {
    const res = await fetch('https://api.github.com/repos/vonish/vonish-ocr/releases/latest', { headers: { Accept: 'application/vnd.github+json' } })
    if (res.ok) {
      const data = await res.json()
      appendLog('info', 'API', `GitHub Releases 最新版本: ${data.tag_name || 'unknown'}`)
      showToast({ type: 'info', message: `最新版本 ${data.tag_name || 'unknown'}`, duration: 2600 })
    } else {
      appendLog('warn', 'API', `GitHub Releases 检查返回 ${res.status}`)
      showToast({ type: 'error', message: '更新检查失败，发布仓库可能未配置', duration: 3200 })
    }
  } catch (e) {
    appendLog('error', 'API', `更新检查失败: ${e.message || e}`)
    showToast({ type: 'error', message: '更新检查失败', duration: 3200 })
  } finally {
    busyAction.value = ''
  }
}

function exportDiagnostics() {
  const data = {
    exported_at: new Date().toISOString(),
    hardware: hardware.value,
    models: models.value,
    localApi: localApi.value,
    queue: queue.value,
    logs: logs.value,
    sysInfo: sysInfo.value,
  }
  downloadBlob(JSON.stringify(data, null, 2), 'vonish-diagnostics.json', 'application/json;charset=utf-8')
  appendLog('info', 'API', '诊断包 JSON 已导出')
}

function seedLogs() {
  return [
    { t: '14:02:33', level: 'info', tag: 'OCR', msg: '#128 completed 340ms 93.3%' },
    { t: '14:02:34', level: 'info', tag: 'MODEL', msg: 'auto -> rapidocr-mobile-cn' },
    { t: '14:02:35', level: 'api', tag: 'API', msg: 'POST /v1/ocr 200 OK 340ms' },
    { t: '14:02:36', level: 'warn', tag: 'QUEUE', msg: '03 pending' },
  ]
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function openConsoleAlert({ title, message, confirmText = '确定' }) {
  consoleDialog.value = { type: 'alert', title, message, confirmText, cancelText: '', resolve: null }
  return new Promise(resolve => {
    consoleDialog.value.resolve = resolve
  })
}

function openConsoleConfirm({ title, message, confirmText = '确定', cancelText = '取消' }) {
  consoleDialog.value = { type: 'confirm', title, message, confirmText, cancelText, resolve: null }
  return new Promise(resolve => {
    consoleDialog.value.resolve = resolve
  })
}

function resolveConsoleDialog(value) {
  const resolve = consoleDialog.value?.resolve
  consoleDialog.value = null
  resolve?.(value)
}
</script>

<style scoped>
.backend-console {
  height: 100vh;
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr);
  gap: var(--layout-gap);
  padding: var(--layout-pad);
  background: var(--v-bg);
  color: var(--v-text);
  animation: console-in 200ms var(--ease-cut);
  overflow: hidden;
}

@keyframes console-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.console-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding-inline: var(--s4);
}

.console-heading {
  display: flex;
  align-items: center;
  gap: var(--s3);
}

.breath-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--v-accent);
  box-shadow: 0 0 12px var(--v-accent-32);
  animation: dot-breath 1600ms var(--ease-cut) infinite;
}

.breath-dot.stopped {
  background: var(--v-error);
  box-shadow: 0 0 12px var(--v-error-dim);
}

@keyframes dot-breath {
  0%, 100% { opacity: 0.42; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1); }
}

.console-kicker,
.mono,
.panel-title,
.request-table,
.terminal,
.queue-strip,
.nameplate {
  font-family: var(--font-mono);
}

.console-kicker {
  margin-top: 2px;
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.console-title {
  margin: 0;
  font-size: 24px;
}

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

.return-btn:hover {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.console-main {
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: var(--s4);
}

.metric-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr 1fr 1fr;
  gap: var(--s4);
}

.metric-card,
.console-panel {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s4);
}

.metric-head,
.endpoint-row,
.status-row,
.button-row,
.log-head,
.system-actions,
.queue-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
}

.metric-head,
.panel-title {
  margin-bottom: var(--s3);
  color: var(--v-text);
  font-weight: var(--fw-semibold);
}

.faint {
  color: var(--v-text-faint);
  font-size: var(--fs-caption);
}

.accent {
  color: var(--v-accent);
}

.gpu-body {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: var(--s4);
  align-items: center;
}

.ring {
  width: 106px;
  height: 106px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(var(--v-accent) var(--pct), var(--v-bg) 0);
  position: relative;
  font-family: var(--font-mono);
  color: var(--v-accent);
}

.ring::after {
  content: "";
  position: absolute;
  inset: 10px;
  background: var(--v-rail);
  border-radius: 50%;
}

.ring span {
  position: relative;
  z-index: 1;
}

.metric-stack {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
}

.readout {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(72px, 1fr) auto;
  gap: var(--s3);
  align-items: baseline;
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.readout b {
  color: var(--v-text);
  font-size: var(--fs-small);
  text-align: right;
  white-space: nowrap;
}

.bar-row {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--s1);
  margin-block: var(--s1);
}

.bar-meta {
  display: grid;
  grid-template-columns: minmax(72px, 1fr) auto;
  gap: var(--s3);
  align-items: baseline;
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.bar-meta b {
  color: var(--v-text);
  white-space: nowrap;
}

.thin-bar {
  height: 4px;
  background: var(--v-bg);
  border-radius: var(--r1);
  overflow: hidden;
}

.thin-bar span {
  display: block;
  height: 100%;
  background: var(--v-accent);
  transition: width var(--dur-base) var(--ease-cut);
}

.bus-line {
  margin-top: var(--s3);
  color: var(--v-text-faint);
  font-size: 9pt;
}

.console-grid {
  display: grid;
  grid-template-columns: minmax(300px, 0.9fr) minmax(420px, 1.35fr);
  gap: var(--s4);
}

.resident-card,
.request-table,
.code-sample {
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  padding: var(--s3);
}

.resident-card {
  display: flex;
  justify-content: space-between;
  gap: var(--s3);
  margin-bottom: var(--s3);
}

.performance-card {
  flex-direction: column;
  align-items: flex-start;
}

.capsule-row,
.profile-row,
.filter-row,
.stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
}

.capsule,
.profile-pill,
.filter-pill,
.secondary-btn,
.primary-btn,
.danger-btn,
.port-btn {
  border-radius: var(--r3);
  min-height: 34px;
  padding-inline: var(--s3);
  border: 1px solid var(--v-border);
  background: transparent;
  color: var(--v-text-muted);
  cursor: pointer;
}

.capsule:disabled,
.profile-pill:disabled,
.secondary-btn:disabled,
.primary-btn:disabled,
.danger-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

.capsule,
.profile-pill {
  min-width: 132px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding-block: var(--s2);
}

.capsule small,
.profile-pill small {
  margin-top: 2px;
  color: var(--v-text-faint);
  font-size: 10px;
}

.capsule.active,
.profile-pill.active,
.filter-pill.active {
  border-color: var(--v-accent);
  color: var(--v-text);
  box-shadow: var(--glow-soft);
}

.capsule.busy,
.profile-pill.busy {
  border-color: var(--v-accent);
  animation: busy-pulse 900ms var(--ease-cut) infinite;
}

@keyframes busy-pulse {
  0%, 100% { box-shadow: none; }
  50% { box-shadow: var(--glow-active); }
}

.capsule.blocked {
  color: var(--v-text-faint);
}

.primary-btn {
  background: var(--v-accent);
  border-color: var(--v-accent);
  color: var(--v-coal);
  font-weight: var(--fw-semibold);
}

.danger-btn {
  border-color: var(--v-error);
  color: var(--v-error);
}

.endpoint {
  color: var(--v-accent);
  font-size: 12pt;
}

.status-row {
  justify-content: flex-start;
  margin-block: var(--s3);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--v-text-faint);
}

.status-dot.running {
  background: var(--v-accent);
}

.port-edit {
  margin-left: auto;
  color: var(--v-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.port-input {
  width: 78px;
  margin-left: var(--s2);
  background: var(--v-bg);
  border: 1px solid var(--v-accent);
  border-radius: var(--r2);
  color: var(--v-text);
  font-family: var(--font-mono);
}

.request-table {
  margin-block: var(--s3);
  font-size: 10pt;
}

.request-head,
.request-row {
  display: grid;
  grid-template-columns: 70px minmax(120px, 1fr) 52px 52px 76px;
  gap: var(--s2);
  min-height: 26px;
  align-items: center;
}

.request-head {
  color: var(--v-text-faint);
  font-size: var(--fs-micro);
}

.request-row {
  color: var(--v-text-muted);
  border-top: 1px solid var(--v-border);
}

.request-row .error {
  color: var(--v-error);
}

.step-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  margin: var(--s3) 0 0;
  padding: 0;
}

.step-list li {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: var(--s3);
  padding: var(--s2) var(--s3);
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
}

.step-list li.current {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.step-list li.done span {
  color: var(--v-accent);
}

.step-list li.error {
  border-color: var(--v-error);
  color: var(--v-error);
}

.step-list small {
  color: var(--v-text-muted);
}

.code-sample {
  margin-top: var(--s3);
  color: var(--v-text-muted);
  font-size: 9pt;
  white-space: pre-wrap;
}

.terminal {
  height: 310px;
  overflow: auto;
  background: #0A0A0A;
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  padding: var(--s3);
  font-size: 10pt;
}

.log-line {
  line-height: 1.6;
  color: var(--v-paper);
  word-break: break-word;
}

.log-line.warn { color: var(--v-format); }
.log-line.error { color: var(--v-error); }
.log-line.api { color: var(--v-accent); }

.queue-strip,
.system-actions,
.nameplate {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s3) var(--s4);
}

.queue-strip {
  justify-content: flex-start;
  color: var(--v-text-muted);
  font-size: 11pt;
}

.queue-strip b {
  color: var(--v-text);
}

.system-actions {
  justify-content: flex-start;
}

.nameplate {
  color: var(--v-text-faint);
  font-size: 9pt;
}

.console-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--v-bg) 78%, transparent);
}

.console-dialog {
  width: min(420px, calc(100vw - 48px));
  background: var(--v-rail);
  border: 1px solid var(--v-border-strong);
  border-radius: var(--r4);
  padding: var(--s5);
  box-shadow: var(--glow-soft);
}

.console-dialog-title {
  font-size: var(--fs-h2);
  margin-bottom: var(--s3);
}

.console-dialog p {
  margin: 0;
  color: var(--v-text-muted);
  line-height: 1.7;
}

.console-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--s3);
  margin-top: var(--s5);
}

@media (max-width: 1180px) {
  .metric-grid,
  .console-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .backend-console {
    padding: var(--s4);
  }

  .metric-grid,
  .console-grid {
    grid-template-columns: 1fr;
  }

  .return-btn {
    min-width: 120px;
  }
}
</style>
