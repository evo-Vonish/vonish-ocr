import { reactive, ref } from 'vue'

const dialogs = reactive([])
let idCounter = 0

function openDialog({ title = '', message = '', type = 'alert', confirmText = '确定', cancelText = '取消' } = {}) {
  const id = ++idCounter
  const dialog = { id, title, message, type, confirmText, cancelText, resolve: null, reject: null }
  dialogs.push(dialog)

  if (type === 'confirm') {
    return new Promise((resolve) => {
      dialog.resolve = resolve
    })
  }
  return Promise.resolve(true)
}

export function vAlert({ title = '提示', message = '', confirmText = '确定' } = {}) {
  return openDialog({ title, message, type: 'alert', confirmText })
}

export function vConfirm({ title = '确认', message = '', confirmText = '确定', cancelText = '取消' } = {}) {
  return openDialog({ title, message, type: 'confirm', confirmText, cancelText })
}

export function useDialog() {
  return {
    dialogs,
    confirmDialog(id) {
      const idx = dialogs.findIndex(d => d.id === id)
      if (idx !== -1) {
        const d = dialogs[idx]
        dialogs.splice(idx, 1)
        if (d.resolve) d.resolve(true)
      }
    },
    cancelDialog(id) {
      const idx = dialogs.findIndex(d => d.id === id)
      if (idx !== -1) {
        const d = dialogs[idx]
        dialogs.splice(idx, 1)
        if (d.resolve) d.resolve(false)
      }
    },
  }
}
