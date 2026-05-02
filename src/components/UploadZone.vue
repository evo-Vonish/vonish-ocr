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
import { ref, computed } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()
const fileInput = ref(null)
const files = ref([])
let idCounter = 0

const selectAll = ref(false)
const selectedFiles = computed(() => files.value.filter(f => f.selected))

function onDrop(e) {
  addFiles(e.dataTransfer.files)
}

function onFileSelect(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function addFiles(items) {
  for (const f of items) {
    if (!f.type.startsWith('image/')) continue
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
    }
  } else {
    // 批量处理
    try {
      const batchResult = await taskStore.submitBatch(selected.map(f => f.base64))
      selected.forEach(f => f.status = 'processing')
      // TODO: 轮询批量任务状态
    } catch (e) {
      selected.forEach(f => f.status = 'failed')
    }
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
</style>
