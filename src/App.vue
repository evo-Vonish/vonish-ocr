<template>
  <div class="app">
    <header class="status-bar">
      <div class="logo">VonishOCR</div>
      <div class="stats">
        <span>模型: {{ configStore.config.ocr_model }}</span>
        <span>队列: {{ taskStore.pendingCount }} 待处理 / {{ taskStore.doneCount }} 已完成</span>
      </div>
      <button class="config-btn" @click="showConfig = true">⚙️ 配置</button>
    </header>
    <main class="main-area">
      <div class="left-panel">
        <UploadZone />
      </div>
      <div class="right-panel">
        <ResultPanel />
      </div>
    </main>
    <ConfigDrawer v-model:visible="showConfig" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTaskStore } from './stores/taskStore'
import { useConfigStore } from './stores/configStore'
import UploadZone from './components/UploadZone.vue'
import ResultPanel from './components/ResultPanel.vue'
import ConfigDrawer from './components/ConfigDrawer.vue'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const showConfig = ref(false)

onMounted(() => {
  configStore.loadConfig()
  configStore.loadModels()
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
}
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.status-bar {
  height: 52px;
  background: #1a1a2e;
  color: #fff;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 20px;
  flex-shrink: 0;
}
.logo {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.5px;
}
.stats {
  flex: 1;
  display: flex;
  gap: 20px;
  font-size: 13px;
  opacity: 0.9;
}
.config-btn {
  background: rgba(255,255,255,0.1);
  border: none;
  color: #fff;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.config-btn:hover { background: rgba(255,255,255,0.2); }
.main-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.left-panel {
  width: 42%;
  border-right: 1px solid #e5e5e5;
  background: #fff;
  overflow-y: auto;
}
.right-panel {
  flex: 1;
  background: #fff;
  overflow-y: auto;
}
</style>
