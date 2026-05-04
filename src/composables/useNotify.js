import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification'
import { getCurrentWindow } from '@tauri-apps/api/window'

let permissionChecked = false
let permissionGranted = false

async function ensurePermission() {
  if (permissionChecked) return permissionGranted
  permissionGranted = await isPermissionGranted()
  if (!permissionGranted) {
    const result = await requestPermission()
    permissionGranted = result === 'granted'
  }
  permissionChecked = true
  return permissionGranted
}

/**
 * 检查窗口是否最小化（仅最小化时才应发送通知，避免打扰用户）
 */
export async function isWindowMinimized() {
  try {
    return await getCurrentWindow().isMinimized()
  } catch {
    // 如果 API 不可用（如浏览器环境），回退到 document.hidden
    return document.hidden
  }
}

/**
 * 发送系统原生通知（仅在窗口最小化时，且用户未关闭通知开关）
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
    sendNotification({ title, body })
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
  console.log('[Notify]', title, body)
  await notify({ title, body })
}

/**
 * 批量 OCR 失败通知
 */
export async function notifyBatchFailed(message) {
  await notify({ title: '批量识别失败', body: message })
}
