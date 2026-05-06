import { ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { useConfigStore } from '../stores/configStore'
import { preprocessImage, getPreprocessImageUrl, parseApiError } from '../api/tauri_ipc'
import { showToast } from './useToast'

const MAX_SIZE = 10 * 1024 * 1024

export function useFileUpload() {
  const taskStore = useTaskStore()
  const configStore = useConfigStore()
  const isPreprocessing = ref(false)

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

  function addFiles(items, { strategy = 'standard', autoPreprocess = true } = {}) {
    const addedTasks = []
    for (const f of items) {
      if (f.type === 'application/pdf') {
        showToast({ type: 'warning', message: `PDF 文件 "${f.name}" 暂不支持，请转换为图片后上传。`, duration: 4000 })
        continue
      }
      if (!f.type.startsWith('image/')) {
        showToast({ type: 'warning', message: `文件 "${f.name}" 不是支持的图片格式。`, duration: 3000 })
        continue
      }
      if (f.size > MAX_SIZE) {
        showToast({ type: 'warning', message: `文件 "${f.name}" 过大，请压缩后重新上传。最大 10MB。`, duration: 5000 })
        continue
      }
      const reader = new FileReader()
      reader.onload = (e) => {
        const [task] = taskStore.addFiles([{
          name: f.name,
          size: f.size,
          status: 'pending',
          selected: true,
          thumb: e.target.result,
          base64: e.target.result,
        }])
        taskStore.setCurrentTask(task.id)
        addedTasks.push(task)
        if (autoPreprocess) {
          runPreprocessPreview(task, strategy)
        }
      }
      reader.readAsDataURL(f)
    }
    return addedTasks
  }

  return {
    isPreprocessing,
    addFiles,
    runPreprocessPreview,
  }
}
