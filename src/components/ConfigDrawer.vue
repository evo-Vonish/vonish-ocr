<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="visible" class="drawer-overlay" @click.self="close">
        <aside class="drawer">
          <header class="drawer-header">
            <div>
              <div class="drawer-kicker">LOCAL SETTINGS</div>
              <h3 class="drawer-title v-title">证据桌配置</h3>
            </div>
            <button class="close-btn" type="button" title="关闭" @click="close">
              <span aria-hidden="true"></span>
            </button>
          </header>

          <div class="drawer-body">
            <section>
              <h4>显示模式</h4>
              <select :value="themeStore.userTheme || 'system'" @change="themeStore.setTheme($event.target.value)">
                <option value="system">跟随系统</option>
                <option value="dark">深色 · 默认证据桌</option>
                <option value="light">亮色 · 白天使用</option>
                <option value="mono">黑白 · 去彩审阅</option>
                <option value="hc">高对比 · 强制可见</option>
              </select>
              <p class="hint-text">当前生效：{{ themeLabel }}</p>
            </section>

            <section>
              <h4>OCR 模型</h4>
              <select v-model="config.ocr_model">
                <option value="rapidocr-mobile-cn">极速 · RapidOCR Mobile</option>
                <option value="cnocr-standard-cn">均衡 · CnOCR</option>
              </select>
            </section>

            <section>
              <h4>预处理</h4>
              <label><input type="checkbox" v-model="config.preprocess" /> 启用预处理</label>
              <label><input type="checkbox" v-model="config.auto_rotate" /> 自动旋转</label>
              <label><input type="checkbox" v-model="config.perspective_correct" /> 透视矫正</label>
              <label><input type="checkbox" v-model="config.scene_detect" /> 场景检测</label>
            </section>

            <section>
              <h4>AI 修复</h4>
              <label><input type="checkbox" v-model="config.ai.enabled" /> 启用 AI 修复</label>
              <select v-model="config.ai.trigger_mode">
                <option value="auto">低置信度自动触发，小于 85%</option>
                <option value="always">每张图都修复</option>
                <option value="manual">仅手动触发</option>
              </select>
              <label><input type="checkbox" v-model="config.batch_ai_refine" /> 批量识别也执行 AI 修复</label>
              <p class="hint-text">批量 AI 修复会逐图调用当前方案，速度和费用都更高，默认关闭。</p>
              <button class="wide-action" type="button" @click="emit('open-ai-center')">打开 API 方案中心</button>
            </section>

            <section>
              <h4>输出选项</h4>
              <select v-model="config.output_mode">
                <option value="raw">原始</option>
                <option value="polished">精修</option>
                <option value="dual">双版本</option>
                <option value="smart">智能</option>
              </select>
              <label><input type="checkbox" v-model="config.include_diff" /> 包含修改记录</label>
            </section>

            <section>
              <h4>启动设置</h4>
              <label><input type="checkbox" v-model="config.preload_model" /> 启动时预加载默认模型</label>
              <p class="hint-text">开启后应用启动会自动加载模型，首次识别无需等待。</p>
            </section>

            <section>
              <h4>系统通知</h4>
              <label><input type="checkbox" v-model="config.notify_enabled" /> 窗口最小化时弹出系统通知</label>
              <p class="hint-text">仅在窗口最小化到任务栏时，批量识别完成后弹出 Windows 原生通知。</p>
              <button class="wide-action" type="button" @click="testNativeNotify">测试系统通知</button>
            </section>

            <section>
              <h4>性能模式</h4>
              <select v-model="config.power_mode">
                <option value="beast">全速 · 占用更多资源</option>
                <option value="balanced">均衡 · 推荐</option>
                <option value="eco">省电 · 低功耗</option>
              </select>
              <p class="hint-text">离电使用时建议切换为省电模式。</p>
            </section>
          </div>

          <footer class="drawer-footer">
            <button class="secondary" type="button" @click="openDir">打开模型目录</button>
            <button class="save-btn" type="button" @click="save" :disabled="configStore.isLoading">
              {{ configStore.isLoading ? '保存中' : '保存' }}
            </button>
          </footer>
        </aside>
      </div>
    </Transition>

  </Teleport>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { useThemeStore } from '../stores/themeStore'
import { showToast } from '../composables/useToast'
import { notify } from '../composables/useNotify'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible', 'open-ai-center'])
const configStore = useConfigStore()
const themeStore = useThemeStore()

const themeNames = {
  dark: '深色证据桌',
  light: '亮色白天',
  mono: '黑白审阅',
  hc: '高对比',
}

const themeLabel = computed(() => themeNames[themeStore.resolvedTheme] || themeStore.resolvedTheme)

function close() {
  emit('update:visible', false)
}

const config = reactive({
  ocr_model: 'auto',
  preprocess: true,
  auto_rotate: true,
  perspective_correct: false,
  scene_detect: true,
  ai: {
    enabled: false,
    provider: 'deepseek',
    api_key: '',
    api_base: '',
    model: '',
  },
  output_mode: 'smart',
  include_diff: false,
  batch_ai_refine: false,
  power_mode: 'balanced',
})

watch(() => props.visible, (v) => {
  if (v) Object.assign(config, JSON.parse(JSON.stringify(configStore.config)))
})

function openDir() {
  configStore.openModelsFolder()
}

async function testNativeNotify() {
  await notify({ title: 'VonishOCR', body: '系统通知已连接。', force: true })
  showToast({ type: 'success', message: '已发送测试通知', duration: 2200 })
}

async function save() {
  try {
    await configStore.updateConfig(config)
    showToast({ type: 'success', message: '配置已保存，下次任务生效', duration: 2000 })
    close()
  } catch (e) {
    showToast({ type: 'error', message: '保存失败: ' + e.message, duration: 4000 })
  }
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 17, 15, 0.72);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: 400px;
  max-width: calc(100vw - 24px);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--v-rail);
  border-left: 1px solid var(--v-border);
  color: var(--v-text);
}

.drawer-header {
  padding: var(--s5);
  border-bottom: 1px solid var(--v-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.08em;
}

.drawer-title {
  margin-top: var(--s1);
  font-size: var(--fs-h2);
}

.close-btn {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  background: transparent;
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  color: var(--v-text-muted);
  cursor: pointer;
}

.close-btn span,
.close-btn span::after {
  width: 14px;
  height: 1px;
  background: currentColor;
  display: block;
}

.close-btn span {
  transform: rotate(45deg);
}

.close-btn span::after {
  content: "";
  transform: rotate(90deg);
}

.close-btn:hover {
  color: var(--v-text);
  border-color: var(--v-accent);
}

.drawer-body {
  flex: 1;
  padding: var(--s5);
  overflow-y: auto;
}

.drawer-body section {
  margin-bottom: var(--s5);
  padding: var(--s4);
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
}

.drawer-body h4 {
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  margin-bottom: var(--s3);
  letter-spacing: 0.04em;
}

.drawer-body label {
  display: flex;
  align-items: center;
  gap: var(--s2);
  margin: var(--s2) 0;
  font-size: var(--fs-small);
  color: var(--v-text-muted);
  cursor: pointer;
}

.drawer-body input[type='checkbox'] {
  accent-color: var(--v-accent);
}

.drawer-body input[type='text'],
.drawer-body input[type='password'],
.drawer-body select {
  width: 100%;
  min-height: 36px;
  padding: var(--s2) var(--s3);
  margin-top: var(--s2);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
  color: var(--v-text);
  outline: none;
  transition: border-color var(--dur-base) var(--ease-cut);
}

.drawer-body input:focus,
.drawer-body select:focus {
  border-color: var(--v-accent);
}

.hint-text {
  font-size: var(--fs-caption);
  color: var(--v-text-muted);
  margin-top: var(--s2);
  line-height: 1.5;
}

.drawer-footer {
  padding: var(--s4) var(--s5);
  border-top: 1px solid var(--v-border);
  display: flex;
  gap: var(--s3);
}

.drawer-footer button {
  flex: 1;
  min-height: 36px;
  border-radius: var(--r3);
  cursor: pointer;
  font-weight: var(--fw-semibold);
}

.secondary {
  background: transparent;
  color: var(--v-text-muted);
  border: 1px solid var(--v-border);
}

.secondary:hover {
  color: var(--v-text);
  border-color: var(--v-border-strong);
}

.save-btn {
  background: var(--v-accent);
  color: var(--v-coal);
  border: 0;
}

.save-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.wide-action {
  width: 100%;
  min-height: 36px;
  margin-top: var(--s3);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  background: var(--v-bg);
  color: var(--v-text);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  cursor: pointer;
}

.wide-action:hover {
  border-color: var(--v-accent);
  box-shadow: var(--glow-soft);
}

.slide-enter-active,
.slide-leave-active {
  transition: opacity var(--dur-base) var(--ease-cut);
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}

</style>
