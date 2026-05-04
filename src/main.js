import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/global.css'
import { showToast } from './composables/useToast'

const app = createApp(App)
app.use(createPinia())

// 全局 Vue 错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('[Vue Error]', err, info)
  showToast({ type: 'error', message: `渲染错误: ${err?.message || err}`, duration: 6000 })
}

// 全局 JS 错误捕获
window.onerror = (msg, url, line) => {
  showToast({ type: 'error', message: `JS 错误: ${msg} (第${line}行)`, duration: 6000 })
}
window.addEventListener('unhandledrejection', (ev) => {
  showToast({ type: 'error', message: `未处理异常: ${ev.reason?.message || ev.reason}`, duration: 6000 })
})

app.mount('#app')
