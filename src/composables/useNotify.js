/**
 * 通知封装 —— 使用 Web Notification API（Tauri WebView2 中天然支持）
 * 替代 tauri-plugin-notification，避免 Windows 上 COM/WinRT 初始化崩溃。
 */

let permissionChecked = false
let permissionGranted = false

async function ensurePermission() {
  if (permissionChecked) return permissionGranted
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') {
    permissionGranted = true
  } else if (Notification.permission !== 'denied') {
    const result = await Notification.requestPermission()
    permissionGranted = result === 'granted'
  }
  permissionChecked = true
  return permissionGranted
}

/**
 * 检查窗口是否最小化（仅最小化时才应发送通知，避免打扰用户）
 */
export async function isWindowMinimized() {
  // Tauri WebView2 中使用 document.hidden 判断窗口是否可见
  return document.hidden
}

/**
 * 发送系统通知（仅在窗口最小化时，且用户未关闭通知开关）
 * @param {Object} options
 * @param {string} options.title
 * @param {string} options.body
 * @param {boolean} [options.force] 强制发送，无视最小化状态
 */
export async function notify({ title, body, force = false } = {}) {
  try {
    if (!force) {
      const minimized = await isWindowMinimized()
      if (!minimized) return
    }
    const ok = await ensurePermission()
    if (!ok) return
    new Notification(title, { body })
  } catch (e) {
    console.warn('通知发送失败:', e)
  }
}

/**
 * 批量 OCR 完成通知
 */
export async function notifyBatchComplete(successCount, failCount, totalCount) {
  const title = failCount > 0 ? '批量识别部分完成' : '批量识别完成'
  const body = `共 ${totalCount} 张：成功 ${successCount} 张${failCount > 0 ? `，失败 ${failCount} 张` : ''}`
  await notify({ title, body })
}

/**
 * 批量 OCR 失败通知
 */
export async function notifyBatchFailed(message) {
  await notify({ title: '批量识别失败', body: message })
}
