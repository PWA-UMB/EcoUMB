// Captura una página PÚBLICA real con Edge/Chrome por DevTools (p. ej. la ejecución del CI en GitHub Actions).
// Uso:  node scripts/capture_page.mjs <URL> <salida.png> [ancho] [alto] [texto_a_esperar]
// El script espera a que aparezca `texto_a_esperar` en la página antes de fotografiarla; si no aparece, falla
// (no se genera una captura de una página a medio cargar).
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const [url, out, w = '1280', h = '1000', waitText = ''] = process.argv.slice(2)
if (!url || !out) throw new Error('Uso: node scripts/capture_page.mjs <URL> <salida.png> [ancho] [alto] [texto]')
const PORT = 9335
const BROWSER = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
].find(existsSync)
if (!BROWSER) throw new Error('No se encontró Edge ni Chrome')

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const proc = spawn(BROWSER, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'ecoumb-page-'))}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' })
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
const evaluate = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result.value

try {
  await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: +w, height: +h, deviceScaleFactor: 1, mobile: false })
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }] })
  await send('Page.navigate', { url })
  const end = Date.now() + 30000
  let ok = false
  while (Date.now() < end) {
    const ready = await evaluate(`document.readyState === 'complete'`).catch(() => false)
    const has = !waitText || (await evaluate(`document.body.innerText.includes(${JSON.stringify(waitText)})`).catch(() => false))
    if (ready && has) { ok = true; break }
    await sleep(500)
  }
  if (!ok) throw new Error(`La página no mostró el texto esperado: "${waitText}"`)
  await sleep(1500) // deja terminar la carga diferida de GitHub
  const { data } = await send('Page.captureScreenshot', { format: 'png' })
  writeFileSync(out, Buffer.from(data, 'base64'))
  console.log('captura:', out, '| título:', await evaluate('document.title'))
} finally {
  ws.close()
  proc.kill()
}
