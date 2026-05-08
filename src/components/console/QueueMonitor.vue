<template>
  <article class="console-panel queue-monitor">
    <div class="queue-head">
      <div>
        <div class="panel-title">队列与任务</div>
        <div class="mono queue-readout">
          WAIT {{ stats.queued || 0 }} · PROC {{ stats.processing || 0 }} · DONE {{ stats.done || 0 }} · FAILED {{ stats.failed || 0 }}
        </div>
      </div>
      <button class="secondary-btn" type="button" @click="loadSnapshot">刷新</button>
    </div>

    <div class="queue-table-head">
      <span>ID</span>
      <span>FILE</span>
      <span>MODEL</span>
      <span>STATUS</span>
      <span>MS</span>
    </div>

    <div class="queue-table">
      <TaskRow
        v-for="task in tasks"
        :key="task.id"
        :task="task"
        :selected="selectedIds.includes(task.id)"
        @toggle="toggleTask"
      />
      <div v-if="!tasks.length" class="queue-empty mono">NO TASKS · WAITING FOR SUBMISSION</div>
    </div>

    <BatchActions
      :selected-ids="selectedIds"
      @cancel-selected="cancelSelected"
      @retry-selected="retrySelected"
      @clear-selection="selectedIds = []"
    />
  </article>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import {
  cancelServiceQueueTask,
  getPythonPort,
  getServiceQueueTasks,
  retryServiceQueueTask,
} from '../../api/tauri_ipc'
import { showToast } from '../../composables/useToast'
import TaskRow from './TaskRow.vue'
import BatchActions from './BatchActions.vue'

const tasks = ref([])
const stats = ref({})
const selectedIds = ref([])
let eventSource = null

onMounted(async () => {
  await loadSnapshot()
  await connectStream()
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
})

async function loadSnapshot() {
  try {
    const data = await getServiceQueueTasks(100)
    applySnapshot(data)
  } catch (e) {
    showToast({ type: 'error', message: `队列读取失败: ${e.message || e}`, duration: 3000 })
  }
}

async function connectStream() {
  try {
    const port = await getPythonPort()
    if (!port) return
    eventSource = new EventSource(`http://127.0.0.1:${port}/v1/queue/stream`)
    eventSource.onmessage = event => {
      try {
        applySnapshot(JSON.parse(event.data))
      } catch {
        // SSE 心跳或异常片段直接忽略，下一次快照会覆盖。
      }
    }
    eventSource.onerror = () => {
      if (eventSource) eventSource.close()
      eventSource = null
      window.setTimeout(connectStream, 2500)
    }
  } catch {
    // 非 Tauri 预览环境下可能没有 sidecar 端口，保留手动刷新。
  }
}

function applySnapshot(data) {
  stats.value = data.stats || {}
  tasks.value = data.tasks || []
  selectedIds.value = selectedIds.value.filter(id => tasks.value.some(task => task.id === id))
}

function toggleTask(id) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter(item => item !== id)
    : [...selectedIds.value, id]
}

async function cancelSelected() {
  await Promise.all(selectedIds.value.map(id => cancelServiceQueueTask(id).catch(() => null)))
  selectedIds.value = []
  await loadSnapshot()
}

async function retrySelected() {
  await Promise.all(selectedIds.value.map(id => retryServiceQueueTask(id).catch(() => null)))
  selectedIds.value = []
  await loadSnapshot()
}
</script>

<style scoped>
.queue-monitor {
  grid-column: 1 / -1;
}

.queue-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s4);
  margin-bottom: var(--s3);
}

.queue-readout {
  margin-top: var(--s1);
  color: var(--v-text-muted);
}

.queue-table-head {
  display: grid;
  grid-template-columns: 78px minmax(0, 1.4fr) 86px 116px 70px;
  gap: var(--s2);
  padding-bottom: var(--s2);
  border-bottom: 1px solid var(--v-border);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-faint);
}

.queue-table {
  max-height: 260px;
  overflow: auto;
}

.queue-empty {
  min-height: 88px;
  display: grid;
  place-items: center;
  color: var(--v-text-faint);
}
</style>
