<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="visible" class="drawer-overlay" @click.self="close">
        <div class="drawer">
          <div class="drawer-header">
            <h3>设置</h3>
            <button class="close-btn" @click="close">✕</button>
          </div>

          <div class="drawer-body">
            <section>
              <h4>OCR 模型</h4>
              <select v-model="config.ocr_model">
                <option value="auto">自动选择</option>
                <option value="rapidocr-mobile-cn">极速版 (RapidOCR Mobile)</option>
                <option value="cnocr-standard-cn">标准版 (CnOCR)</option>
                <option value="paddleocr-vl-1.5">专业版 (PaddleOCR)</option>
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
              <select v-model="config.ai.provider">
                <option value="deepseek">DeepSeek</option>
                <option value="openai">OpenAI</option>
                <option value="qwen">Qwen</option>
                <option value="custom">自定义</option>
              </select>
              <input v-model="config.ai.api_key" type="password" placeholder="API Key" />
              <input v-model="config.ai.api_base" type="text" placeholder="Base URL (可选)" />
              <input v-model="config.ai.model" type="text" placeholder="模型名 (可选)" />
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
              <h4>功耗模式</h4>
              <select v-model="config.power_mode">
                <option value="performance">性能优先</option>
                <option value="balanced">均衡</option>
                <option value="save">省电</option>
              </select>
            </section>
          </div>

          <div class="drawer-footer">
            <button class="secondary" @click="openDir">📁 打开模型目录</button>
            <button class="save-btn" @click="save" :disabled="configStore.isLoading">
              {{ configStore.isLoading ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { useConfigStore } from '../stores/configStore'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])
const configStore = useConfigStore()

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
  power_mode: 'balanced',
})

// 打开抽屉时从 store 同步配置
watch(() => props.visible, (v) => {
  if (v) {
    Object.assign(config, JSON.parse(JSON.stringify(configStore.config)))
  }
})

function openDir() {
  configStore.openModelsFolder()
}

async function save() {
  try {
    await configStore.updateConfig(config)
    close()
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: 380px;
  background: #fff;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.08);
}
.drawer-header {
  padding: 18px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.drawer-header h3 { font-size: 16px; font-weight: 600; }
.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #8e8e93;
}
.drawer-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
.drawer-body section { margin-bottom: 24px; }
.drawer-body h4 {
  font-size: 12px;
  color: #8e8e93;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.drawer-body label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  font-size: 13px;
  cursor: pointer;
}
.drawer-body input[type='text'],
.drawer-body input[type='password'],
.drawer-body select {
  width: 100%;
  padding: 10px 12px;
  margin-top: 8px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}
.drawer-body input:focus,
.drawer-body select:focus {
  border-color: #1a1a2e;
}
.drawer-footer {
  padding: 14px 20px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 10px;
}
.drawer-footer button {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  border: none;
}
.secondary {
  background: #f2f2f7;
  color: #333;
}
.secondary:hover { background: #e5e5ea; }
.save-btn {
  background: #1a1a2e;
  color: #fff;
}
.save-btn:hover { opacity: 0.9; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.slide-enter-active,
.slide-leave-active { transition: opacity 0.2s ease; }
.slide-enter-from,
.slide-leave-to { opacity: 0; }
</style>
