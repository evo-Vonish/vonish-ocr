import { execFile } from 'node:child_process'
import { platform } from 'node:os'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)
const port = Number(process.argv[2] || 1420)

async function main() {
  if (platform() !== 'win32') return
  const pids = new Set()

  try {
    const { stdout } = await execFileAsync('netstat', ['-ano', '-p', 'tcp'])
    for (const line of stdout.split(/\r?\n/)) {
      const parts = line.trim().split(/\s+/)
      if (parts.length < 5 || parts[0] !== 'TCP') continue
      const local = parts[1]
      const state = parts[3]
      const pid = parts[4]
      if (state === 'LISTENING' && local.endsWith(`:${port}`)) {
        pids.add(pid)
      }
    }
  } catch {
    // Fall through to PowerShell based detection below.
  }

  try {
    const script = [
      `Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue`,
      'Where-Object { $_.State -eq "Listen" }',
      'Select-Object -ExpandProperty OwningProcess -Unique',
    ].join(' | ')
    const { stdout } = await execFileAsync('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script])
    for (const pid of stdout.split(/\r?\n/).map(value => value.trim()).filter(Boolean)) {
      pids.add(pid)
    }
  } catch {
    // Some Windows editions restrict Get-NetTCPConnection; netstat above is enough there.
  }

  for (const pid of pids) {
    if (pid && pid !== '0') {
      await execFileAsync('taskkill', ['/PID', pid, '/T', '/F']).catch(() => {})
      console.log(`Freed Vite port ${port} from PID ${pid}`)
    }
  }
}

main().catch(error => {
  console.warn(`Port cleanup skipped: ${error.message}`)
})
