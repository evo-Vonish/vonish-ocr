<template>
  <div class="upload-zone">
    <div
      class="drop-area"
      @dragover.prevent
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <p class="hint">📁 拖放图片到此处，或点击选择文件</p>
      <p class="sub">支持 JPG / PNG / WEBP / BMP，单次最多 200 张</p>
      <input ref="fileInput" type="file" multiple accept="image/*" @change="onFileSelect" hidden />
    </div>

    <!-- 批量进度条 -->
    <div v-if="batchProgress.total > 0" class="batch-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: (batchProgress.completed / batchProgress.total * 100) + '%' }"></div>
      </div>
      <div class="progress-info">
        <span>{{ batchProgress.completed }} / {{ batchProgress.total }} 张</span>
        <span v-if="batchProgress.speed > 0">{{ batchProgress.speed.toFixed(1) }} 张/秒</span>
        <button v-if="batchProgress.status === 'processing'" class="cancel-btn" @click="cancelBatch">取消</button>
      </div>
    </div>

    <div class="file-list" v-if="files.length">
      <div class="toolbar">
        <label class="check-all">
          <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" />
          <span>全选</span>
        </label>
        <div class="actions">
          <button @click="clearCompleted">清空已完成</button>
          <button class="primary" @click="startOCR" :disabled="!selectedFiles.length || taskStore.isProcessing">
            {{ taskStore.isProcessing ? '识别中...' : `开始识别 (${selectedFiles.length})` }}
          </button>
        </div>
      </div>

      <div v-for="file in files" :key="file.id" class="file-item" :class="file.status" @click="selectFile(file)">
        <input type="checkbox" v-model="file.selected" @click.stop />
        <img v-if="file.thumb" :src="file.thumb" class="thumb" />
        <div class="info">
          <div class="name">{{ file.name }}</div>
          <div class="meta">{{ formatSize(file.size) }} · {{ statusText(file.status) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { ocrBatch, createBatchWebSocket, cancelBatch as apiCancelBatch } from '../api/tauri_ipc'

const taskStore = useTaskStore()
const fileInput = ref(null)
const files = ref([])
let idCounter = 0

const selectAll = ref(false)
const selectedFiles = computed(() => files.value.filter(f => f.selected))

// 批量进度状态
const batchProgress = reactive({
  taskId: null,
  total: 0,
  completed: 0,
  status: '',
  speed: 0,
  startTime: 0,
})
let ws = null

function onDrop(e) {
  addFiles(e.dataTransfer.files)
}

function onFileSelect(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function addFiles(items) {
  const MAX_SIZE = 10 * 1024 * 1024 // 10MB
  for (const f of items) {
    if (!f.type.startsWith('image/')) continue
    if (f.size > MAX_SIZE) {
      alert(`文件 "${f.name}" 过大 (${(f.size / 1024 / 1024).toFixed(1)}MB)，请压缩后重新上传（最大 10MB）`)
      continue
    }
    const reader = new FileReader()
    reader.onload = (e) => {
      const fileData = {
        id: ++idCounter,
        name: f.name,
        size: f.size,
        status: 'pending',
        selected: true,
        thumb: e.target.result,
        base64: e.target.result,
      }
      files.value.push(fileData)
      taskStore.addFiles([fileData])
    }
    reader.readAsDataURL(f)
  }
}

function toggleSelectAll() {
  files.value.forEach(f => f.selected = selectAll.value)
}

function clearCompleted() {
  const completed = files.value.filter(f => f.status === 'done')
  completed.forEach(f => taskStore.removeTask(f.id))
  files.value = files.value.filter(f => f.status !== 'done')
}

function selectFile(file) {
  taskStore.currentTask = file
}

async function startOCR() {
  const selected = selectedFiles.value
  if (!selected.length) return

  selected.forEach(f => f.status = 'queued')

  if (selected.length === 1) {
    const file = selected[0]
    file.status = 'processing'
    try {
      const result = await taskStore.recognizeSingle(file.base64)
      taskStore.setResult(file.id, result)
      file.status = 'done'
    } catch (e) {
      file.status = 'failed'
      // 解析后端错误响应
      let errCode = 'UNKNOWN'
      let errMsg = '识别失败，请重试'
      try {
        const parsed = typeof e === 'string' ? JSON.parse(e) : e
        if (parsed?.detail?.code) {
          errCode = parsed.detail.code
          errMsg = parsed.detail.message
        } else if (parsed?.message) {
          errMsg = parsed.message
        }
      } catch (_) {
        if (typeof e === 'string') errMsg = e
      }
      taskStore.setError(file.id, { code: errCode, message: errMsg })
    }
    return
  }

  // 批量处理
  taskStore.isProcessing = true
  selected.forEach(f => f.status = 'processing')
  batchProgress.total = selected.length
  batchProgress.completed = 0
  batchProgress.status = 'processing'
  batchProgress.startTime = Date.now()
  batchProgress.speed = 0

  try {
    const { task_id } = await ocrBatch(selected.map(f => f.base64))
    batchProgress.taskId = task_id

    // 建立 WebSocket 连接监听进度
    ws = await createBatchWebSocket(task_id, (msg) => {
      if (msg.type === 'progress') {
        batchProgress.completed = msg.completed
        const elapsedSec = (Date.now() - batchProgress.startTime) / 1000
        batchProgress.speed = elapsedSec > 0 ? msg.completed / elapsedSec : 0

        // 更新已完成文件的状态
        for (let i = 0; i < msg.completed && i < selected.length; i++) {
          if (selected[i].status !== 'done') {
            selected[i].status = 'done'
          }
        }
      }
    })

    // 等待 WebSocket 关闭或任务完成
    await new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (batchProgress.completed >= batchProgress.total || batchProgress.status === 'cancelled') {
          clearInterval(checkInterval)
          resolve()
        }
      }, 500)
      // 超时保护：60秒
      setTimeout(() => {
        clearInterval(checkInterval)
        resolve()
      }, 60000)
    })

    if (batchProgress.status !== 'cancelled') {
      batchProgress.status = 'completed'
    }
  } catch (e) {
    console.error('批量识别失败:', e)
    let errCode = 'UNKNOWN'
    let errMsg = '批量识别失败，请重试'
    try {
      const parsed = typeof e === 'string' ? JSON.parse(e) : e
      if (parsed?.detail?.code) {
        errCode = parsed.detail.code
        errMsg = parsed.detail.message
      } else if (parsed?.message) {
        errMsg = parsed.message
      }
    } catch (_) {
      if (typeof e === 'string') errMsg = e
    }
    selected.forEach(f => {
      f.status = 'failed'
      taskStore.setError(f.id, { code: errCode, message: errMsg })
    })
  } finally {
    taskStore.isProcessing = false
    if (ws) {
      ws.close()
      ws = null
    }
    // 3秒后隐藏进度条
    setTimeout(() => {
      if (batchProgress.status !== 'processing') {
        batchProgress.total = 0
        batchProgress.completed = 0
      }
    }, 3000)
  }
}

async function cancelBatch() {
  if (!batchProgress.taskId) return
  try {
    await apiCancelBatch(batchProgress.taskId)
    batchProgress.status = 'cancelled'
    if (ws) {
      ws.close()
      ws = null
    }
  } catch (e) {
    console.error('取消失败:', e)
  }
}

function formatSize(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / (1024 * 1024)).toFixed(1) + ' MB'
}

function statusText(s) {
  const map = { pending: '待处理', queued: '排队中', processing: '处理中', done: '已完成', failed: '失败' }
  return map[s] || s
}
</script>

<style scoped>
.upload-zone {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.drop-area {
  border: 2px dashed #d1d1d6;
  border-radius: 12px;
  padding: 40px 24px;
  text-align: center;
  color: #8e8e93;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}
.drop-area:hover {
  border-color: #1a1a2e;
  color: #1a1a2e;
  background: #f2f2f7;
}
.hint { font-size: 15px; font-weight: 500; margin-bottom: 6px; }
.sub { font-size: 12px; }
.file-list { margin-top: 16px; flex: 1; overflow-y: auto; }
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}
.check-all { display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; }
.actions { display: flex; gap: 8px; }
button {
  padding: 6px 14px;
  border: 1px solid #d1d1d6;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
button:hover { border-color: #1a1a2e; }
button.primary {
  background: #1a1a2e;
  color: #fff;
  border-color: #1a1a2e;
}
button:disabled { opacity: 0.4; cursor: not-allowed; }
.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  transition: background 0.15s;
  cursor: pointer;
}
.file-item:hover { background: #f9f9fb; }
.file-item.processing { background: #e6f2ff; }
.file-item.done { background: #f0fff4; }
.file-item.failed { background: #fff0f0; }
.thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #e5e5e5;
}
.info { flex: 1; min-width: 0; }
.name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta { font-size: 11px; color: #8e8e93; margin-top: 2px; }

.batch-progress {
  margin: 12px 0;
  padding: 12px 16px;
  background: #f9f9fb;
  border-radius: 10px;
  border: 1px solid #e5e5e5;
}
.progress-bar {
  height: 8px;
  background: #e5e5e5;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-fill {
  height: 100%;
  background: #1a1a2e;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #666;
}
.cancel-btn {
  padding: 4px 10px;
  border: 1px solid #ff4d4f;
  background: #fff;
  color: #ff4d4f;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.cancel-btn:hover {
  background: #ff4d4f;
  color: #fff;
}
</style>
