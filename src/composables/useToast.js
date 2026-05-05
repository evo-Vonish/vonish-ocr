import { reactive } from 'vue'

const toasts = reactive([])
let idCounter = 0

export function useToast() {
  return {
    toasts,
    showToast,
    dismissToast,
  }
}

export function showToast({ type = 'info', message = '', duration = 4000 } = {}) {
  const id = ++idCounter
  const toast = { id, type, message, duration }
  toasts.push(toast)
  if (duration > 0) {
    setTimeout(() => dismissToast(id), duration)
  }
  return id
}

export function dismissToast(id) {
  const idx = toasts.findIndex(t => t.id === id)
  if (idx !== -1) toasts.splice(idx, 1)
}
