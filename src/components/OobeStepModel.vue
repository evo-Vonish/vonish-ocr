<template>
  <div class="oobe-step">
    <h1 class="oobe-step-title">{{ t('oobe_model_title') }}</h1>
    <p class="oobe-step-subtitle">{{ t('oobe_model_subtitle') }}</p>

    <div class="oobe-model-list">
      <!-- Ultra -->
      <div class="v-card oobe-model-card is-resident"
        :class="{ 'is-active': oobeData.models.ultra.active }"
        @click="selectModel('ultra')"
      >
        <div class="oobe-model-header">
          <span class="oobe-model-tier">{{ t('oobe_model_ultra') }}</span>
          <span class="oobe-model-badge">{{ t('oobe_model_resident') }}</span>
        </div>
        <div class="oobe-model-name">{{ t('oobe_model_rapidocr') }}</div>
        <div class="oobe-model-spec">{{ t('oobe_model_rapidocr_spec') }}</div>
      </div>

      <!-- Standard -->
      <div
        class="v-card oobe-model-card"
        :class="{ 'is-resident': standardInstalled, 'is-active': oobeData.models.standard.active, 'is-muted': standardSkipped }"
        @click="selectModel('standard')"
      >
        <div class="oobe-model-header">
          <span class="oobe-model-tier">{{ t('oobe_model_standard') }}</span>
          <span v-if="standardInstalled" class="oobe-model-badge">{{ t('oobe_model_resident') }}</span>
        </div>
        <div class="oobe-model-name">{{ t('oobe_model_cnocr') }}</div>
        <div class="oobe-model-spec">{{ t('oobe_model_cnocr_spec') }}</div>
        <div class="oobe-model-actions">
          <template v-if="!standardInstalled && !standardDownloading && !standardSkipped">
            <button class="oobe-btn-outline" @click.stop="downloadModel('standard')">{{ t('oobe_model_download') }}</button>
            <button class="oobe-btn-ghost-small" @click.stop="skipModel('standard')">{{ t('oobe_model_skip') }}</button>
          </template>
          <template v-else-if="standardDownloading">
            <div class="oobe-model-progress">
              <div class="v-progress">
                <div class="v-progress-fill" :style="{ width: standardProgress + '%' }"></div>
              </div>
              <span class="oobe-model-progress-text">{{ standardProgress }}%</span>
            </div>
          </template>
          <template v-else-if="standardSkipped">
            <span class="oobe-model-skipped">{{ t('oobe_model_skip') }}</span>
          </template>
        </div>
      </div>

      <!-- Pro -->
      <div
        class="v-card oobe-model-card"
        :class="{ 'is-resident': proInstalled, 'is-active': oobeData.models.pro.active, 'is-muted': proSkipped }"
        @click="selectModel('pro')"
      >
        <div class="oobe-model-header">
          <span class="oobe-model-tier">{{ t('oobe_model_pro') }}</span>
          <span v-if="proInstalled" class="oobe-model-badge">{{ t('oobe_model_resident') }}</span>
        </div>
        <div class="oobe-model-name">{{ t('oobe_model_onnxtr') }}</div>
        <div class="oobe-model-spec">{{ t('oobe_model_onnxtr_spec') }}</div>
        <div class="oobe-model-actions">
          <template v-if="!proInstalled && !proDownloading && !proSkipped">
            <button class="oobe-btn-outline" @click.stop="downloadModel('pro')">{{ t('oobe_model_download') }}</button>
            <button class="oobe-btn-ghost-small" @click.stop="skipModel('pro')">{{ t('oobe_model_skip') }}</button>
          </template>
          <template v-else-if="proDownloading">
            <div class="oobe-model-progress">
              <div class="v-progress">
                <div class="v-progress-fill" :style="{ width: proProgress + '%' }"></div>
              </div>
              <span class="oobe-model-progress-text">{{ proProgress }}%</span>
            </div>
          </template>
          <template v-else-if="proSkipped">
            <span class="oobe-model-skipped">{{ t('oobe_model_skip') }}</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, watch } from 'vue'
import { t } from '../i18n'
import { useConfigStore } from '../stores/configStore'

const oobeData = inject('oobeData')
const configStore = useConfigStore()

const standardInstalled = computed(() => oobeData.models.standard.installed)
const standardDownloading = computed(() => oobeData.models.standard.downloading)
const standardProgress = computed(() => oobeData.models.standard.progress)
const standardSkipped = computed(() => oobeData.models.standard.skipped)

const proInstalled = computed(() => oobeData.models.pro.installed)
const proDownloading = computed(() => oobeData.models.pro.downloading)
const proProgress = computed(() => oobeData.models.pro.progress)
const proSkipped = computed(() => oobeData.models.pro.skipped)

watch(() => configStore.pullProgress, (pp) => {
  if (!pp) return
  if (pp.modelId === 'cnocr-standard-cn') {
    oobeData.models.standard.downloading = pp.status === 'downloading'
    oobeData.models.standard.progress = pp.progress
    if (pp.status === 'completed') {
      oobeData.models.standard.installed = true
      oobeData.models.standard.active = true
    }
  }
  if (pp.modelId === 'onnxtr-standard') {
    oobeData.models.pro.downloading = pp.status === 'downloading'
    oobeData.models.pro.progress = pp.progress
    if (pp.status === 'completed') {
      oobeData.models.pro.installed = true
      oobeData.models.pro.active = true
    }
  }
})

watch(() => configStore.models, syncInstalledModels, { deep: true })

onMounted(() => {
  syncInstalledModels()
})

async function downloadModel(tier) {
  const model = oobeData.models[tier]
  model.downloading = true
  model.progress = 0
  try {
    await configStore.downloadModel(model.id)
    model.installed = true
    selectModel(tier)
  } catch (e) {
    console.error('model download failed:', e)
  } finally {
    model.downloading = false
  }
}

function skipModel(tier) {
  oobeData.models[tier].skipped = true
  oobeData.models[tier].active = false
  if (!oobeData.models.ultra.active && !oobeData.models.standard.active && !oobeData.models.pro.active) {
    oobeData.models.ultra.active = true
  }
}

function syncInstalledModels() {
  const local = configStore.models?.local || configStore.models?.models || []
  const ids = new Set(local.map(m => m.id || m.model_id || m.name).filter(Boolean))
  if (ids.has(oobeData.models.standard.id)) {
    oobeData.models.standard.installed = true
  }
  if (ids.has(oobeData.models.pro.id)) {
    oobeData.models.pro.installed = true
  }
}

function selectModel(tier) {
  const model = oobeData.models[tier]
  if (!model?.installed || model.skipped || model.downloading) return
  Object.values(oobeData.models).forEach(item => { item.active = false })
  model.active = true
}
</script>

<style scoped>
.oobe-step {
  position: relative;
}

.oobe-step-title {
  font-family: var(--font-title);
  font-size: var(--fs-display);
  font-weight: var(--fw-bold);
  color: var(--v-text);
  line-height: 1.18;
  margin-bottom: var(--s2);
}

.oobe-step-subtitle {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  color: var(--v-text-muted);
  line-height: 1.6;
  margin-bottom: var(--s6);
}

.oobe-model-list {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}

.oobe-model-card {
  padding: var(--s4);
  position: relative;
  overflow: hidden;
}

.oobe-model-card.is-resident::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--v-accent);
}

.oobe-model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--s1);
}

.oobe-model-tier {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
  letter-spacing: 0.06em;
}

.oobe-model-badge {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
  border: 1px solid var(--v-accent);
  border-radius: var(--r1);
  padding: 1px 4px;
}

.oobe-model-name {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  font-weight: var(--fw-semibold);
  color: var(--v-text);
  margin-bottom: var(--s1);
}

.oobe-model-spec {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  margin-bottom: var(--s3);
}

.oobe-model-actions {
  display: flex;
  gap: var(--s3);
  align-items: center;
}

.oobe-btn-outline {
  height: 28px;
  padding-inline: var(--s4);
  background: transparent;
  border: 1px solid var(--v-accent);
  border-radius: var(--r3);
  color: var(--v-accent);
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  cursor: pointer;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-btn-outline:hover {
  background: var(--v-accent);
  color: var(--v-coal);
}

.oobe-btn-ghost-small {
  height: 28px;
  padding-inline: var(--s3);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--r3);
  color: var(--v-text-muted);
  font-family: var(--font-body);
  font-size: var(--fs-caption);
  cursor: pointer;
  transition: all var(--dur-base) var(--ease-cut);
}

.oobe-btn-ghost-small:hover {
  color: var(--v-text);
  border-color: var(--v-border);
}

.oobe-model-progress {
  display: flex;
  align-items: center;
  gap: var(--s3);
  width: 100%;
}

.oobe-model-progress .v-progress {
  flex: 1;
  margin-top: 0;
}

.oobe-model-progress-text {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-accent);
  min-width: 32px;
  text-align: right;
}

.oobe-model-skipped {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
}
</style>
