// Captura la PWA REAL en ejecución (Docker compose) con Edge/Chrome por el protocolo DevTools.
// No simula nada: navega, llena los formularios, envía y fotografía lo que el navegador dibuja.
// Uso:  node scripts/capture_ui.mjs [URL_PWA] [carpeta_salida]
// Requiere: `docker compose up -d` corriendo, Node >= 22 y Edge o Chrome instalado.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const PWA = (process.argv[2] ?? 'http://localhost:5173').replace(/\/$/, '')
const OUT = process.argv[3] ?? 'docs/evidencias/capturas'
const PORT = 9333
const BROWSERS = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
]
const browserPath = BROWSERS.find(existsSync)
if (!browserPath) throw new Error('No se encontró Edge ni Chrome')
mkdirSync(OUT, { recursive: true })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const profile = mkdtempSync(join(tmpdir(), 'ecoumb-cap-'))
const proc = spawn(
  browserPath,
  ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', 'about:blank'],
  { stdio: 'ignore' },
)

async function connect() {
  for (let i = 0; i < 40; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
      const page = pages.find((p) => p.type === 'page')
      if (page) return page.webSocketDebuggerUrl
    } catch { /* el navegador aún arranca */ }
    await sleep(250)
  }
  throw new Error('No se pudo conectar al navegador')
}

const ws = new WebSocket(await connect())
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject })
let nextId = 0
const pending = new Map()
const network = new Map() // requestId -> { method, url }
const apiLog = []
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data)
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id)
    pending.delete(msg.id)
    msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result)
  } else if (msg.method === 'Network.requestWillBeSent') {
    network.set(msg.params.requestId, { method: msg.params.request.method, url: msg.params.request.url })
  } else if (msg.method === 'Network.responseReceived') {
    const req = network.get(msg.params.requestId)
    if (req && req.url.includes('/api/v1/')) {
      apiLog.push(`${new Date().toISOString().slice(11, 19)}  ${req.method.padEnd(4)} ${new URL(req.url).pathname.padEnd(24)} -> HTTP ${msg.params.response.status}`)
    }
  }
}
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const id = ++nextId
    pending.set(id, { resolve, reject })
    ws.send(JSON.stringify({ id, method, params }))
  })
const evaluate = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? 'error de evaluación')
  return r.result.value
}
const waitFor = async (expression, label, timeout = 8000) => {
  const end = Date.now() + timeout
  while (Date.now() < end) {
    if (await evaluate(expression).catch(() => false)) return
    await sleep(150)
  }
  throw new Error(`Tiempo agotado esperando: ${label}`)
}
const shot = async (name) => {
  await sleep(350) // deja terminar transiciones y fuentes
  const { data } = await send('Page.captureScreenshot', { format: 'png' })
  writeFileSync(join(OUT, name), Buffer.from(data, 'base64'))
  console.log('captura:', name)
}
const goto = async (path) => {
  await send('Page.navigate', { url: `${PWA}${path}` })
  await waitFor(`document.readyState === 'complete' && !!document.querySelector('h1, main')`, `cargar ${path}`)
}
const setDesktop = () => send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false })
const setPhone = () => send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
const fill = (label, value) =>
  evaluate(`(() => {
    const lab = [...document.querySelectorAll('label')].find(l => l.textContent.trim() === ${JSON.stringify(label)});
    const el = document.getElementById(lab.htmlFor);
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event('input', { bubbles: true }));
  })()`)
const click = (text) => evaluate(`[...document.querySelectorAll('button, a')].find(b => b.textContent.trim().startsWith(${JSON.stringify(text)})).click()`)
const heading = () => evaluate(`document.querySelector('h1')?.textContent ?? ''`)

try {
  await send('Page.enable')
  await send('Network.enable')
  const email = `captura.${Date.now()}@umb.edu.co`
  const password = 'Clave-Segura-2026'
  const name = 'Laura Gómez'

  await setDesktop()
  await goto('/login')
  await shot('pwa-01-login-escritorio.png')

  await goto('/registro')
  await click('Crear cuenta') // envío vacío: se ve la validación en el cliente
  await waitFor(`document.body.innerText.includes('Ingresa tu correo')`, 'errores de validación')
  await shot('pwa-02-registro-validacion.png')

  await fill('Nombre (opcional)', name)
  await fill('Correo electrónico', email)
  await fill('Contraseña', password)
  await fill('Confirmar contraseña', password)
  await click('Crear cuenta')
  await waitFor(`location.pathname === '/login'`, 'redirección al login')
  await waitFor(`document.body.innerText.includes('Cuenta creada')`, 'aviso de cuenta creada')
  await shot('pwa-03-login-cuenta-creada.png')

  await fill('Contraseña', password)
  await click('Iniciar sesión')
  await waitFor(`location.pathname === '/' && document.querySelector('h1')?.textContent === ${JSON.stringify(name)}`, 'Home')
  await shot('pwa-04-home-escritorio.png')

  await goto('/') // recarga completa: la sesión debe persistir
  await waitFor(`document.querySelector('h1')?.textContent === ${JSON.stringify(name)}`, 'Home tras recargar')
  console.log('sesión persiste tras recargar: sí (Home muestra', await heading(), ')')
  await setPhone()
  await sleep(300)
  await shot('pwa-05-home-movil.png')
  await click('Cerrar sesión')
  await waitFor(`location.pathname === '/login'`, 'logout')
  await shot('pwa-06-login-movil.png')

  // Correo repetido (409): se ve el error en el campo de correo
  await setDesktop()
  await goto('/registro')
  await fill('Correo electrónico', email)
  await fill('Contraseña', password)
  await fill('Confirmar contraseña', password)
  await click('Crear cuenta')
  await waitFor(`document.body.innerText.includes('Ya existe una cuenta con este correo')`, 'error 409 en el formulario')
  await shot('pwa-07-registro-correo-repetido-409.png')

  const header = `# Solicitudes a la API vistas por el navegador (equivalente a la pestaña Network)  |  ${new Date().toISOString().slice(0, 16).replace('T', ' ')}\n# PWA: ${PWA}\n\n`
  writeFileSync(join(OUT, '..', 'red-navegador.txt'), header + apiLog.join('\n') + '\n')
  console.log('\n' + apiLog.join('\n'))
} finally {
  ws.close()
  proc.kill()
}
