/**
 * 通知封装 — Tauri 原生吐司优先（应用名 + 系统提示音），Web Notification 兜底
 */
let tauriAvailable = false
let tauriNotif = null
let tauriInitTried = false

async function initTauriNotif() {
  if (tauriInitTried) return tauriAvailable
  tauriInitTried = true
  if (!(typeof window !== 'undefined' && window.__TAURI_INTERNALS__)) return false
  try {
    const mod = await import('@tauri-apps/plugin-notification')
    tauriNotif = mod
    tauriAvailable = true
    return true
  } catch (e) {
    console.warn('Tauri 通知插件未就绪（需 cargo build），降级到 Web:', e.message || e)
  }
  return false
}

export async function isWindowMinimized() {
  return document.hidden
}

async function sendViaTauri(title, body) {
  if (!tauriAvailable) return false
  try {
    const fn = tauriNotif?.sendNotification
      || tauriNotif?.default?.sendNotification
    if (!fn) return false
    // Tauri 原生 Windows 吐司：应用名=VonishOCR，带系统提示音
    fn({ title, body })
    return true
  } catch (e) {
    console.warn('Tauri 通知失败:', e.message || e)
  }
  return false
}

function sendViaWeb(title, body) {
  if (!('Notification' in window)) return false
  if (Notification.permission !== 'granted') return false
  try {
    new Notification(title, {
      body,
      icon: '/logo.svg',
      silent: false,
    })
    return true
  } catch (e) {
    return false
  }
}

export async function notify({ title, body, force = false } = {}) {
  try {
    if (!force) {
      const minimized = await isWindowMinimized()
      if (!minimized) return
    }

    // 每次尝试初始化 Tauri（确保重试）
    await initTauriNotif()

    // Tauri 原生优先（应用名正确 + 系统提示音）
    if (tauriAvailable) {
      const sent = await sendViaTauri(title, body)
      if (sent) return
    }

    // Web 兜底（仅 permission 已 grant 时生效）
    sendViaWeb(title, body)
  } catch (e) {
    console.warn('通知发送失败:', e)
  }
}

export async function notifyBatchComplete(successCount, failCount, totalCount) {
  const title = failCount > 0 ? '批量识别部分完成' : '批量识别完成'
  const body = `共 ${totalCount} 张：成功 ${successCount} 张${failCount > 0 ? `，失败 ${failCount} 张` : ''}`
  await notify({ title, body, force: true })
}

export async function notifyBatchFailed(message) {
  await notify({ title: '批量识别失败', body: message, force: true })
}
