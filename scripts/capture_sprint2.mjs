// Recorre el flujo del Sprint 2 en la PWA REAL (Docker compose) con Edge/Chrome por el protocolo DevTools:
// perfil, captura por cámara y por galería, clasificación simulada, historial e instalabilidad.
// Usa una cámara de prueba del propio navegador (flags --use-fake-*), no simula la respuesta de la API.
// Uso:  node scripts/capture_sprint2.mjs [URL_PWA] [URL_API] [carpeta_salida]
// Requiere: `docker compose up -d` corriendo, Node >= 22 y Edge o Chrome instalado.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { crc32, deflateSync } from 'node:zlib'

const PWA = (process.argv[2] ?? 'http://localhost:5173').replace(/\/$/, '')
const API = (process.argv[3] ?? 'http://localhost:8000').replace(/\/$/, '')
const OUT = process.argv[4] ?? 'docs/evidencias/capturas'
const PORT = 9334
const BROWSERS = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
]
const browserPath = BROWSERS.find(existsSync)
if (!browserPath) throw new Error('No se encontró Edge ni Chrome')
mkdirSync(OUT, { recursive: true })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const scratch = mkdtempSync(join(tmpdir(), 'ecoumb-s2-'))

/** PNG sólido de 640x480 con un degradado vertical: una imagen real y distinta por color, sin dependencias. */
function makePng(path, [r, g, b]) {
  const width = 640
  const height = 480
  const raw = Buffer.alloc((width * 3 + 1) * height)
  for (let y = 0; y < height; y++) {
    const row = y * (width * 3 + 1)
    const shade = 0.5 + (0.5 * y) / height
    for (let x = 0; x < width; x++) {
      raw[row + 1 + x * 3] = Math.round(r * shade)
      raw[row + 2 + x * 3] = Math.round(g * shade)
      raw[row + 3 + x * 3] = Math.round(b * shade)
    }
  }
  const chunk = (type, data) => {
    const head = Buffer.alloc(4)
    head.writeUInt32BE(data.length)
    const body = Buffer.concat([Buffer.from(type), data])
    const tail = Buffer.alloc(4)
    tail.writeUInt32BE(crc32(body))
    return Buffer.concat([head, body, tail])
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(width, 0)
  ihdr.writeUInt32BE(height, 4)
  ihdr.set([8, 2, 0, 0, 0], 8)
  writeFileSync(
    path,
    Buffer.concat([
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
      chunk('IHDR', ihdr),
      chunk('IDAT', deflateSync(raw)),
      chunk('IEND', Buffer.alloc(0)),
    ]),
  )
  return path
}

const proc = spawn(
  browserPath,
  [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${mkdtempSync(join(tmpdir(), 'ecoumb-prof-'))}`,
    '--no-first-run',
    '--disable-gpu',
    '--use-fake-device-for-media-stream',
    '--use-fake-ui-for-media-stream',
    'about:blank',
  ],
  { stdio: 'ignore' },
)

async function connect() {
  for (let i = 0; i < 40; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
      const page = pages.find((p) => p.type === 'page')
      if (page) return page.webSocketDebuggerUrl
    } catch {
      /* el navegador aún arranca */
    }
    await sleep(250)
  }
  throw new Error('No se pudo conectar al navegador')
}

const ws = new WebSocket(await connect())
await new Promise((resolve, reject) => {
  ws.onopen = resolve
  ws.onerror = reject
})
let nextId = 0
const pending = new Map()
const network = new Map()
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
      const path = new URL(req.url).pathname
      apiLog.push(`${new Date().toISOString().slice(11, 19)}  ${req.method.padEnd(5)} ${path.padEnd(52)} -> HTTP ${msg.params.response.status}`)
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
const waitFor = async (expression, label, timeout = 10000) => {
  const end = Date.now() + timeout
  while (Date.now() < end) {
    if (await evaluate(expression).catch(() => false)) return
    await sleep(150)
  }
  const seen = await evaluate('location.href + " :: " + document.body.innerText.slice(0, 200)').catch(() => '?')
  throw new Error(`Tiempo agotado esperando: ${label} (página: ${seen})`)
}
const shot = async (name) => {
  await sleep(500)
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
const fill = async (label, value) => {
  await waitFor(`[...document.querySelectorAll('label')].some(l => l.textContent.trim() === ${JSON.stringify(label)})`, `campo ${label}`)
  return evaluate(`(() => {
    const lab = [...document.querySelectorAll('label')].find(l => l.textContent.trim() === ${JSON.stringify(label)});
    const el = document.getElementById(lab.htmlFor);
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event('input', { bubbles: true }));
  })()`)
}
const click = (text) =>
  evaluate(`(() => { const b = [...document.querySelectorAll('button, a')].find(b => b.textContent.trim().startsWith(${JSON.stringify(text)})); if (!b) throw new Error('sin botón ${text}'); b.click() })()`)
const clickNav = (text) =>
  evaluate(`[...document.querySelectorAll('nav a')].find(a => a.textContent.trim() === ${JSON.stringify(text)}).click()`)
const h1 = () => evaluate(`document.querySelector('h1')?.textContent ?? ''`)
const bodyHas = (text) => `document.body.innerText.includes(${JSON.stringify(text)})`

async function chooseFile(path) {
  const { root } = await send('DOM.getDocument')
  const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: 'input[type=file]' })
  await send('DOM.setFileInputFiles', { files: [path], nodeId })
}

const results = []
async function classifyAndReport(label) {
  await click('Clasificar')
  await waitFor(`!!document.querySelector('article[aria-labelledby=result-title]')`, 'resultado de clasificación')
  const summary = await evaluate(`(() => {
    const a = document.querySelector('article[aria-labelledby=result-title]');
    return { title: a.querySelector('h2').textContent, text: a.innerText.replace(/\\n+/g, ' | ') }
  })()`)
  results.push(`${label}: ${summary.text}`)
  return summary
}

try {
  await send('Page.enable')
  await send('Network.enable')
  await send('DOM.enable')

  // Cuenta nueva por la API (el registro por la interfaz ya quedó evidenciado en el Sprint 1).
  const email = `sprint2.${Date.now()}@umb.edu.co`
  const password = 'Clave-Segura-2026'
  const reg = await fetch(`${API}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: 'Laura Gómez' }),
  })
  if (reg.status !== 201) throw new Error(`No se pudo crear la cuenta de prueba: HTTP ${reg.status}`)

  await setDesktop()
  await goto('/login')
  await fill('Correo electrónico', email)
  await fill('Contraseña', password)
  await click('Iniciar sesión')
  await waitFor(`location.pathname === '/' && document.querySelector('h1')?.textContent === 'Laura Gómez'`, 'Home')
  await waitFor(bodyHas('Aún no has clasificado ningún residuo.'), 'historial vacío en Home')
  await shot('s2-01-inicio-escritorio.png')

  // --- Instalabilidad PWA (criterio de aceptación del Sprint 2) ---
  await evaluate('navigator.serviceWorker.ready.then(() => true)') // el SW debe estar activo para ser instalable
  const retry = async (method) => {
    for (let i = 0; i < 20; i++) {
      try {
        return await send(method)
      } catch (error) {
        if (i === 19) throw error
        await sleep(750) // DevTools tarda un instante en poder evaluar el manifiesto
      }
    }
  }
  const installErrors = await retry('Page.getInstallabilityErrors')
  const manifest = await retry('Page.getAppManifest')
  const swScope = await evaluate(`navigator.serviceWorker.getRegistration().then(r => r ? r.scope + ' (activo: ' + !!r.active + ')' : 'sin Service Worker')`)
  const installReport = [
    `# Instalabilidad de la PWA  |  ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
    `# Comprobado con Edge por DevTools (Page.getInstallabilityErrors / Page.getAppManifest) sobre ${PWA}`,
    '',
    `Errores de instalabilidad : ${installErrors.installabilityErrors.length === 0 ? 'ninguno' : JSON.stringify(installErrors.installabilityErrors)}`,
    `Service Worker            : ${swScope}`,
    `Manifiesto                : ${manifest.url}`,
    `  (errores del manifiesto : ${manifest.errors.length === 0 ? 'ninguno' : JSON.stringify(manifest.errors)})`,
    '',
    JSON.stringify(JSON.parse(manifest.data || '{}'), null, 2),
    '',
  ].join('\n')
  writeFileSync(join(OUT, '..', 'pwa-instalabilidad.txt'), installReport)
  console.log(installReport.split('\n').slice(0, 6).join('\n'))

  // --- Escanear: cámara (RF-09) ---
  await setPhone()
  await clickNav('Escanear')
  await waitFor(`location.pathname === '/escanear' && ${bodyHas('Abrir la cámara')}`, 'pantalla Escanear')
  await shot('s2-02-escanear-opciones-movil.png')

  await click('Abrir la cámara')
  await waitFor(`(() => { const v = document.querySelector('video'); return !!v && v.videoWidth > 0 })()`, 'cámara en vivo')
  await shot('s2-03-camara-en-vivo-movil.png')
  await click('Tomar foto')
  await waitFor(bodyHas('Clasificar') + ` && !!document.querySelector('img[alt="Vista previa del residuo"]')`, 'vista previa')
  await shot('s2-04-vista-previa-movil.png')
  await classifyAndReport('cámara')
  await shot('s2-05-resultado-camara-movil.png')

  // --- Escanear: galería (RF-10), varias imágenes distintas ---
  // Las cuatro primeras siempre; las siguientes solo hasta que aparezca un caso de confianza baja (el resultado es
  // determinista por imagen, así que es repetible: el gris (185,185,185) cae en esa banda) para dejar evidencia de ese estado.
  const colors = { verde: [60, 160, 80], azul: [50, 100, 190], rojo: [200, 70, 60], amarillo: [220, 190, 60], gris: [185, 185, 185], morado: [130, 70, 170], naranja: [230, 130, 40], cian: [40, 170, 190], rosa: [220, 100, 150] }
  const BASE_COUNT = 4
  let n = 0
  for (const [name, rgb] of Object.entries(colors)) {
    if (n >= BASE_COUNT && results.some((r) => r.startsWith('BAJA'))) break
    await click('Escanear otro residuo')
    await waitFor(bodyHas('Elegir de la galería'), 'volver a elegir')
    await chooseFile(makePng(join(scratch, `${name}.png`), rgb))
    await waitFor(`!!document.querySelector('img[alt="Vista previa del residuo"]')`, `vista previa ${name}`)
    if (n === 0) await shot('s2-06-vista-previa-galeria-movil.png')
    const summary = await classifyAndReport(`galería (${name})`)
    if (n === 0) await shot('s2-07-resultado-galeria-movil.png')
    if (summary.text.includes('Confianza baja') && !results.some((r) => r.startsWith('BAJA'))) {
      await shot('s2-08-resultado-confianza-baja-movil.png')
      results.push('BAJA: captura tomada')
    }
    n++
  }

  // --- La foto es privada: sin token no se descarga ---
  const list = await (async () => {
    const login = await (await fetch(`${API}/api/v1/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) })).json()
    const me = await (await fetch(`${API}/api/v1/classifications/me?limit=1`, { headers: { Authorization: `Bearer ${login.access_token}` } })).json()
    const imageUrl = `${API}${me.items[0].image_url}`
    const anonymous = await fetch(imageUrl)
    const owner = await fetch(imageUrl, { headers: { Authorization: `Bearer ${login.access_token}` } })
    return { anonymous: anonymous.status, owner: owner.status, type: owner.headers.get('content-type') }
  })()
  console.log('foto sin token:', list.anonymous, '| con token del dueño:', list.owner, list.type)

  // --- Historial (RF-16, RF-17) ---
  await clickNav('Historial')
  await waitFor(`location.pathname === '/historial' && document.querySelectorAll('ul[aria-label=Clasificaciones] li').length >= 5`, 'lista de historial')
  await waitFor(`[...document.querySelectorAll('ul[aria-label=Clasificaciones] img')].every(i => i.alt.startsWith('Foto de'))`, 'miniaturas cargadas')
  await shot('s2-09-historial-movil.png')
  await setDesktop()
  await sleep(300)
  await shot('s2-10-historial-escritorio.png')

  // --- Perfil (RF-04) ---
  await clickNav('Perfil')
  await waitFor(`location.pathname === '/perfil' && ${bodyHas('Mi perfil')}`, 'pantalla Perfil')
  await shot('s2-11-perfil-escritorio.png')
  await fill('Nombre', 'Laura Gómez Pinto')
  await click('Guardar cambios')
  await waitFor(bodyHas('Perfil actualizado.'), 'confirmación del perfil')
  await shot('s2-12-perfil-actualizado-escritorio.png')

  await clickNav('Inicio')
  await waitFor(`document.querySelector('h1')?.textContent === 'Laura Gómez Pinto' && !!document.querySelector('ul[aria-label="Últimas clasificaciones"]')`, 'Home con nombre nuevo y últimas clasificaciones')
  await shot('s2-13-inicio-con-clasificaciones-escritorio.png')

  // Recarga completa: el nombre nuevo viene del servidor, no de la memoria.
  await goto('/perfil')
  await waitFor(`document.getElementById([...document.querySelectorAll('label')].find(l => l.textContent.trim() === 'Nombre').htmlFor).value === 'Laura Gómez Pinto'`, 'nombre persistido')
  console.log('nombre persistido tras recargar: sí')

  const header = `# Solicitudes a la API vistas por el navegador en el recorrido del Sprint 2  |  ${new Date().toISOString().slice(0, 16).replace('T', ' ')}\n# PWA: ${PWA}\n\n`
  writeFileSync(join(OUT, '..', 'red-navegador-sprint2.txt'), header + apiLog.join('\n') + '\n')
  writeFileSync(
    join(OUT, '..', 'sprint2-resultados.txt'),
    [`# Resultados de clasificación devueltos por la API en el recorrido real (simulados, deterministas por foto)`, '', ...results, '', `Foto sin token: HTTP ${list.anonymous}`, `Foto con token del dueño: HTTP ${list.owner} (${list.type})`, ''].join('\n'),
  )
  console.log('\n' + results.join('\n'))
  console.log('\n' + apiLog.join('\n'))
} finally {
  ws.close()
  proc.kill()
}
process.on('unhandledRejection', (error) => {
  console.error(error)
  proc.kill()
  process.exit(1)
})
