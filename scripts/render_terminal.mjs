// Convierte SALIDAS REALES de terminal (ya capturadas en docs/evidencias/*.txt) en imágenes PNG.
// No inventa contenido: dibuja el texto tal como se guardó y lo rotula como "salida de terminal real",
// para no confundirlo con una captura de pantalla de una aplicación.
// Uso:  node scripts/render_terminal.mjs        (requiere Node >= 22 y Edge o Chrome)
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const EV = 'docs/evidencias'
const OUT = join(EV, 'capturas')
const PORT = 9334
const LINE_H = 21
const BROWSER = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
].find(existsSync)
if (!BROWSER) throw new Error('No se encontró Edge ni Chrome')
mkdirSync(OUT, { recursive: true })

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
function colorize(line) {
  const e = esc(line)
  if (line.startsWith('$ ') || line.startsWith('# ')) return `<span class="c">${e}</span>`
  if (/^OK |PASSED|passed|healthy|No new upgrade/.test(line)) return `<span class="ok">${e}</span>`
  if (/^FALLA| FAILED/.test(line)) return `<span class="bad">${e}</span>`
  return e
}
const page = (title, stamp, lines) => `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:#0b1220}
.bar{background:#111a2e;color:#94a3b8;font:13px 'Segoe UI',sans-serif;padding:10px 20px;border-bottom:1px solid #1e293b;display:flex;justify-content:space-between;gap:32px}
.bar b{color:#e2e8f0}
pre{margin:0;padding:16px 20px 20px;color:#e2e8f0;font:15px/${LINE_H}px Consolas,'Cascadia Mono',monospace;white-space:pre}
.c{color:#7dd3fc}.ok{color:#4ade80}.bad{color:#f87171}
</style></head><body><div class="bar"><span><b>${esc(title)}</b> — salida de terminal real (texto capturado sin editar)</span><span>${esc(stamp)}</span></div>
<pre>${lines.map(colorize).join('\n')}</pre></body></html>`

const read = (name) => readFileSync(join(EV, name), 'utf-8').split(/\r?\n/).map((l) => l.trimEnd())
const trimEnd = (a) => { const r = [...a]; while (r.length && !r.at(-1)) r.pop(); return r }

const compose = read('docker-postgres.txt')
const split = compose.findIndex((l) => l.startsWith('$ psql \\dt'))
const pytest = read('backend-pytest.txt')
const covStart = pytest.findIndex((l) => l.includes('tests coverage'))
const jobs = [
  ['term-01-docker-compose-ps.png', 'docker compose up — servicios y arranque de la API', compose.slice(0, split)],
  ['term-02-postgres-tablas-y-seed.png', 'PostgreSQL 16 — tablas, tipos ENUM, seed y alembic check', [compose[0], '', ...compose.slice(split)]],
  ['term-03-postgres-downgrade.png', 'Alembic sobre PostgreSQL 16 — downgrade / upgrade / seed idempotente', read('docker-postgres-downgrade.txt')],
  ['term-04-smoke-contenedores.png', 'Prueba de humo contra los contenedores', read('docker-smoke.txt')],
  ['term-05-pytest-cobertura.png', 'pytest --cov — backend', [pytest[0], '', ...pytest.slice(covStart)]],
]

const profile = mkdtempSync(join(tmpdir(), 'ecoumb-term-'))
const proc = spawn(BROWSER, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
async function wsUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
      const p = pages.find((x) => x.type === 'page')
      if (p) return p.webSocketDebuggerUrl
    } catch { /* arrancando */ }
    await sleep(250)
  }
  throw new Error('No se pudo conectar al navegador')
}
const ws = new WebSocket(await wsUrl())
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
let id = 0
const waiting = new Map()
ws.onmessage = ({ data }) => { const m = JSON.parse(data); if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id) } }
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; waiting.set(i, (m) => (m.error ? rej(new Error(m.error.message)) : res(m.result))); ws.send(JSON.stringify({ id: i, method, params })) })

try {
  await send('Page.enable')
  const { frameTree } = await send('Page.getFrameTree')
  for (const [name, title, raw] of jobs) {
    const lines = trimEnd(raw)
    const width = Math.max(1100, Math.min(1700, Math.round(Math.max(...lines.map((l) => l.length)) * 9.2) + 60))
    const height = lines.length * LINE_H + 100
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false })
    await send('Page.setDocumentContent', { frameId: frameTree.frame.id, html: page(title, `docs/evidencias · ${name}`, lines) })
    await sleep(500)
    const { data } = await send('Page.captureScreenshot', { format: 'png' })
    writeFileSync(join(OUT, name), Buffer.from(data, 'base64'))
    console.log('imagen:', name, `${width}x${height}`)
  }
} finally {
  ws.close()
  proc.kill()
}
