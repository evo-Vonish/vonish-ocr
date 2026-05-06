<template>
  <section class="workbench-upload">
    <div
      class="drop-area"
      :class="{ active: isDragging, processing: taskStore.isProcessing }"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <input ref="fileInput" type="file" multiple accept="image/*,.pdf" @change="onFileSelect" hidden />
      <div v-if="isPreprocessReady || isPreprocessing" class="preprocess-preview" @click.stop>
        <div class="prep-split">
          <figure class="prep-frame original">
            <figcaption>ORIGINAL EVIDENCE</figcaption>
            <img v-if="currentPreprocess?.original_full_url" :src="currentPreprocess.original_full_url" alt="" />
            <img v-else-if="currentFile?.thumb" :src="currentFile.thumb" alt="" />
          </figure>
          <figure class="prep-frame processed" :class="{ fallback: currentPreprocess?.fallback }">
            <figcaption>PREPROCESS RESULT</figcaption>
            <img v-if="currentPreprocess?.processed_full_url" :src="currentPreprocess.processed_full_url" alt="" />
            <div v-else class="prep-wait">PREPROCESSING</div>
          </figure>
        </div>
        <div class="prep-actions">
          <div class="prep-tags">
            <span v-for="(step, i) in currentPreprocess?.steps_applied || []" :key="i" class="prep-tag">
              {{ step.name || step }}
            </span>
            <span v-if="currentPreprocess?.frontend_scene" class="prep-tag accent">
              {{ currentPreprocess.frontend_scene }} · {{ Math.round((currentPreprocess.scene_confidence || 0) * 100) }}%
            </span>
          </div>
          <div class="prep-buttons">
            <button class="text-btn" type="button" @click.stop="strategyPickerOpen = !strategyPickerOpen">重新处理</button>
            <button class="text-btn" type="button" @click.stop="skipCurrentPreprocess">跳过预处理</button>
            <button class="start-btn compact pulse" type="button" :disabled="isPreprocessing" @click.stop="continueCurrentWithPreprocess">继续识别</button>
          </div>
        </div>
        <div v-if="strategyPickerOpen" class="strategy-popover" @click.stop>
          <div class="strategy-title">预处理策略</div>
          <button type="button" :class="{ active: selectedStrategy === 'light' }" @click="applyPreprocessStrategy('light')">轻量 · deskew / CLAHE</button>
          <button type="button" :class="{ active: selectedStrategy === 'standard' }" @click="applyPreprocessStrategy('standard')">标准 · deskew / CLAHE / 去噪</button>
          <button type="button" :class="{ active: selectedStrategy === 'heavy' }" @click="applyPreprocessStrategy('heavy')">深度 · NLM / 去阴影 / 锐化</button>
        </div>
      </div>
      <div v-else-if="taskStore.isProcessing" class="preview-stage">
        <div class="paper-sheet">
          <span class="doc-line wide"></span>
          <span class="doc-line"></span>
          <span class="doc-line short"></span>
          <span class="doc-crease"></span>
          <span class="v-scan-line"></span>
        </div>
        <div class="pipeline">
          <div class="pipeline-node is-done"><span></span>LOAD IMAGE</div>
          <div class="pipeline-node is-current"><span></span>LOCAL OCR</div>
          <div class="pipeline-node"><span></span>AUDIT RESULT</div>
        </div>
      </div>
      <div v-else class="empty-copy">
        <EmptyState />
        <div class="local-idle">LOCAL HELD · DROP OR CLICK</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { useConfigStore } from '../stores/configStore'
import { parseApiError, preprocessImage, getPreprocessImageUrl } from '../api/tauri_ipc'
import { showToast } from '../composables/useToast'
import { useFileUpload } from '../composables/useFileUpload'
import EmptyState from './EmptyState.vue'

const taskStore = useTaskStore()
const configStore = useConfigStore()
const { addFiles, isPreprocessing } = useFileUpload()

const fileInput = ref(null)
const isDragging = ref(false)

const currentFile = computed(() => taskStore.currentTask)
const currentPreprocess = computed(() => currentFile.value ? taskStore.getPreprocessJob(currentFile.value.id) : null)
const isPreprocessReady = computed(() => currentPreprocess.value && currentFile.value?.status === 'pending')
const strategyPickerOpen = ref(false)
const selectedStrategy = ref('standard')

function onDrop(e) {
  isDragging.value = false
  addFiles(e.dataTransfer.files, { strategy: selectedStrategy.value })
}

function onFileSelect(e) {
  addFiles(e.target.files, { strategy: selectedStrategy.value })
  e.target.value = ''
}

async function runPreprocessPreview(file, strategy = 'standard') {
  if (!file?.base64) return
  isPreprocessing.value = true
  taskStore.setPipelineStage('preprocess')
  try {
    const job = await preprocessImage({
      image: file.base64,
      file: file.name,
      strategy,
      config_override: configStore.config.preprocess_config || {},
    })
    const [originalUrl, processedUrl] = await Promise.all([
      getPreprocessImageUrl(job.job_id, 'original'),
      getPreprocessImageUrl(job.job_id, 'processed'),
    ])
    taskStore.setPreprocessJob(file.id, {
      ...job,
      original_full_url: originalUrl,
      processed_full_url: processedUrl,
    })
    taskStore.setPipelineStage('preprocess_ready')
  } catch (e) {
    const err = parseApiError(e, '预处理失败，已保留原图路径')
    taskStore.setError(file.id, err)
    showToast({ type: 'warning', message: `${file.name}: ${err.message}`, duration: 4000 })
    taskStore.setPipelineStage('idle')
  } finally {
    isPreprocessing.value = false
  }
}

async function applyPreprocessStrategy(strategy) {
  selectedStrategy.value = strategy
  strategyPickerOpen.value = false
  if (currentFile.value) {
    await runPreprocessPreview(currentFile.value, strategy)
  }
}

async function continueCurrentWithPreprocess() {
  const file = currentFile.value
  if (!file) return
  await recognizeOne(file, currentPreprocess.value ? { preprocess_job_id: currentPreprocess.value.job_id } : {})
}

async function skipCurrentPreprocess() {
  const file = currentFile.value
  if (!file) return
  await recognizeOne(file, { skip_preprocess: true })
}

async function recognizeOne(file, options = {}) {
  taskStore.setCurrentTask(file.id)
  taskStore.setTaskStatus(file.id, 'processing')
  taskStore.setPipelineStage('ocr')
  try {
    const result = await taskStore.recognizeSingle(file.base64, options)
    taskStore.setResult(file.id, result)
    taskStore.setTaskStatus(file.id, 'done')
    taskStore.setPipelineStage('complete')
  } catch (e) {
    const err = parseApiError(e, '识别失败，请重试')
    taskStore.setTaskStatus(file.id, 'failed')
    taskStore.setError(file.id, err)
    taskStore.setPipelineStage('error')
    showToast({ type: 'error', message: `${file.name}: ${err.message}`, duration: 5000 })
  }
}
</script>

<style scoped>
.workbench-upload {
  min-height: 100%;
}

.drop-area {
  min-height: calc(100vh - 220px);
  display: grid;
  place-items: center;
  background: var(--v-bg);
  border: 2px dashed var(--v-paper);
  border-radius: var(--r4);
  color: var(--v-text-muted);
  cursor: pointer;
  padding: var(--s8);
  transition:
    border-color var(--dur-base) var(--ease-cut),
    box-shadow var(--dur-base) var(--ease-cut),
    background-color var(--dur-base) var(--ease-cut);
}

.drop-area:hover,
.drop-area.active {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
  background: color-mix(in srgb, var(--v-bg) 86%, var(--v-accent-dim) 14%);
}

.empty-copy {
  text-align: center;
}

.empty-title {
  text-align: center;
}

.empty-subtitle {
  margin-top: var(--s3);
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  text-align: center;
}

.local-idle {
  margin-top: var(--s6);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
}

.preprocess-preview {
  width: min(980px, 100%);
  display: grid;
  gap: var(--s4);
  cursor: default;
}

.prep-split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1px minmax(0, 1fr);
  gap: var(--s4);
  align-items: stretch;
}

.prep-split::before {
  content: "";
  grid-column: 2;
  background: var(--v-border);
}

.prep-frame {
  min-height: 320px;
  margin: 0;
  padding: var(--s3);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--s2);
  background: var(--v-panel);
  border-radius: var(--r3);
  overflow: hidden;
}

.prep-frame.original {
  border: 1px dashed var(--v-border);
  background: var(--v-bg);
}

.prep-frame.processed {
  border: 1px solid var(--v-accent);
  animation: prepSlideIn 300ms var(--ease-cut);
}

.prep-frame.processed.fallback {
  border-color: var(--v-error);
}

.prep-frame figcaption {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}

.prep-frame.processed figcaption {
  color: var(--v-accent);
}

.prep-frame img {
  width: 100%;
  height: 100%;
  min-height: 260px;
  object-fit: contain;
}

.prep-wait {
  display: grid;
  place-items: center;
  font-family: var(--font-mono);
  color: var(--v-accent);
}

.prep-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s4);
}

.prep-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s1);
}

.prep-tag {
  border: 1px solid var(--v-border);
  border-radius: var(--r2);
  background: var(--v-rail);
  color: var(--v-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  padding: 2px var(--s2);
  animation: prepTagIn 180ms var(--ease-cut) both;
}

.prep-tag.accent {
  color: var(--v-accent);
  border-color: var(--v-accent);
}

.prep-buttons {
  display: flex;
  gap: var(--s2);
  position: relative;
}

.start-btn.pulse {
  box-shadow: var(--glow-active);
  animation: prepPulse 1600ms var(--ease-cut) infinite;
}

.strategy-popover {
  justify-self: end;
  width: 280px;
  display: grid;
  gap: var(--s2);
  padding: var(--s3);
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
}

.strategy-title {
  font-weight: var(--fw-semibold);
  color: var(--v-text);
}

.strategy-popover button {
  min-height: 34px;
  text-align: left;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: transparent;
  color: var(--v-text-muted);
  cursor: pointer;
  padding-inline: var(--s3);
}

.strategy-popover button.active {
  color: var(--v-text);
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

@keyframes prepSlideIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes prepTagIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes prepPulse {
  0%, 100% { box-shadow: var(--glow-soft); }
  50% { box-shadow: var(--glow-active); }
}

.preview-stage {
  width: min(620px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px;
  gap: var(--s5);
  align-items: center;
}

.paper-sheet {
  position: relative;
  min-height: 320px;
  background: var(--v-paper);
  color: var(--v-coal);
  border-radius: var(--r3);
  overflow: hidden;
  padding: var(--s8);
}

.doc-line {
  display: block;
  height: 6px;
  width: 70%;
  margin-bottom: var(--s4);
  background: color-mix(in srgb, var(--v-coal) 54%, transparent);
  border-radius: var(--r1);
}

.doc-line.wide {
  width: 86%;
}

.doc-line.short {
  width: 44%;
}

.doc-crease {
  position: absolute;
  top: 15%;
  left: 58%;
  width: 1px;
  height: 70%;
  background: color-mix(in srgb, var(--v-coal) 36%, transparent);
  transform: rotate(-8deg);
}

.pipeline {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}

.pipeline-node {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  align-items: center;
  gap: var(--s2);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--v-text-muted);
}

.pipeline-node span {
  width: 8px;
  height: 8px;
  border: 1px solid var(--v-border);
  border-radius: 50%;
}

.pipeline-node.is-done,
.pipeline-node.is-current {
  color: var(--v-accent);
}

.pipeline-node.is-done span {
  background: var(--v-accent);
  border-color: var(--v-accent);
}

.pipeline-node.is-current span {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

@media (max-width: 767px) {
  .drop-area {
    min-height: 360px;
    padding: var(--s5);
  }

  .preview-stage {
    grid-template-columns: 1fr;
  }
}
</style>
