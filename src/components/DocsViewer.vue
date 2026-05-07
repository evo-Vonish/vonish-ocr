<template>
  <section class="docs-viewer">
    <header class="docs-top">
      <div class="docs-heading">
        <span class="breath-dot" aria-hidden="true"></span>
        <div>
          <h1 class="docs-title v-title">卷宗室</h1>
          <div class="docs-kicker">VonishOCR · TECHNICAL REFERENCE</div>
        </div>
      </div>
      <button class="return-btn" type="button" @click="$emit('close')">← 返回证据桌</button>
    </header>

    <main class="docs-main">
      <div v-if="loading" class="docs-loading">
        <div class="paper-stage">
          <span class="doc-line wide"></span>
          <span class="doc-line"></span>
          <span class="doc-line short"></span>
          <span class="v-scan-line"></span>
        </div>
        <div class="loading-text v-mono-accent">加载文档站</div>
      </div>
      <iframe
        ref="docsFrame"
        :src="docsUrl"
        class="docs-frame"
        :class="{ ready: !loading }"
        @load="onLoad"
        @error="onError"
      />
    </main>
  </section>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { getPythonPort } from '../api/tauri_ipc'
import { useThemeStore } from '../stores/themeStore'

defineEmits(['close'])

const docsFrame = ref(null)
const loading = ref(true)
const docsUrl = ref('about:blank')
const docsPort = ref(0)
const themeStore = useThemeStore()

const themedDocsUrl = computed(() => {
  if (!docsPort.value) return 'about:blank'
  const style = encodeURIComponent(themeStore.resolvedStyle || 'desk')
  const mode = encodeURIComponent(themeStore.resolvedMode || 'dark')
  return `http://127.0.0.1:${docsPort.value}/reference/?themeStyle=${style}&themeMode=${mode}`
})

onMounted(async () => {
  try {
    docsPort.value = await getPythonPort()
    docsUrl.value = themedDocsUrl.value
  } catch (e) {
    docsUrl.value = 'about:blank'
    console.error('获取后端端口失败，无法加载文档站:', e)
  }
})

watch(themedDocsUrl, (url) => {
  if (url !== 'about:blank') {
    loading.value = true
    docsUrl.value = url
  }
})

function onLoad() {
  loading.value = false
}

function onError(e) {
  console.warn('文档站 iframe 加载异常:', e)
  loading.value = false
}
</script>

<style scoped>
.docs-viewer {
  height: 100vh;
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr);
  gap: var(--layout-gap);
  padding: var(--layout-pad);
  background: var(--v-bg);
  color: var(--v-text);
  animation: docs-in 200ms var(--ease-cut);
  overflow: hidden;
}

@keyframes docs-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.docs-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding-inline: var(--s4);
}

.docs-heading {
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

@keyframes dot-breath {
  0%, 100% { opacity: 0.42; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1); }
}

.docs-kicker {
  margin-top: 2px;
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.docs-title {
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

.docs-main {
  min-height: 0;
  overflow: hidden;
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  position: relative;
}

.docs-frame {
  width: 100%;
  height: 100%;
  border: none;
  opacity: 0;
  transition: opacity 200ms var(--ease-cut);
}

.docs-frame.ready {
  opacity: 1;
}

.docs-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s4);
  background: var(--v-bg);
  z-index: 1;
}

.paper-stage {
  width: 280px;
  padding: var(--s5);
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  display: flex;
  flex-direction: column;
  gap: var(--s3);
  position: relative;
  overflow: hidden;
}

.doc-line {
  height: 8px;
  background: var(--v-border);
  border-radius: var(--r1);
}

.doc-line.wide { width: 100%; }
.doc-line.short { width: 60%; }

.v-scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--v-accent);
  box-shadow: var(--glow-active);
  animation: v-scan-breathe var(--dur-scan) steps(5) infinite;
}

@keyframes v-scan-breathe {
  0% { transform: translateY(0); opacity: 0.24; }
  50% { transform: translateY(120px); opacity: 1; }
  100% { transform: translateY(0); opacity: 0.24; }
}

.loading-text {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  letter-spacing: 0.08em;
}

@media (max-width: 760px) {
  .docs-viewer {
    padding: var(--s4);
  }

  .return-btn {
    min-width: 120px;
  }
}
</style>
