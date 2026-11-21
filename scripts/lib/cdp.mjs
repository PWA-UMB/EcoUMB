// Cliente mínimo del protocolo DevTools para Edge/Chrome: lo usan los scripts que recorren la PWA real.
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BROWSERS = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
]

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/** Abre el navegador sin interfaz y devuelve las operaciones que necesitan los recorridos. */
export async function launch({ port, pwa, outDir }) {
  const browserPath = BROWSERS.find(existsSync)
  if (!browserPath) throw new Error('No se encontró Edge ni Chrome')
  const proc = spawn(
    browserPath,
    [
      '--headless=new',
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${mkdtempSync(join(tmpdir(), 'ecoumb-prof-'))}`,
      '--no-first-run',
      '--disable-gpu',
      'about:blank',
    ],
    { stdio: 'ignore' },
  )

  let wsUrl = null
  for (let i = 0; i < 40 && !wsUrl; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
      wsUrl = pages.find((p) => p.type === 'page')?.webSocketDebuggerUrl ?? null
    } catch {
      /* el navegador aún arranca */
    }
    if (!wsUrl) await sleep(250)
  }
  if (!wsUrl) throw new Error('No se pudo conectar al navegador')

  const ws = new WebSocket(wsUrl)
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
      if (req?.url.includes('/api/v1/')) {
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
  const bodyHas = (text) => `document.body.innerText.includes(${JSON.stringify(text)})`

  return {
    send,
    evaluate,
    waitFor,
    bodyHas,
    apiLog,
    shot: async (name) => {
      await sleep(500)
      const { data } = await send('Page.captureScreenshot', { format: 'png' })
      writeFileSync(join(outDir, name), Buffer.from(data, 'base64'))
      console.log('captura:', name)
    },
    goto: async (path) => {
      await send('Page.navigate', { url: `${pwa}${path}` })
      await waitFor(`document.readyState === 'complete' && !!document.querySelector('h1, main')`, `cargar ${path}`)
    },
    setDesktop: () => send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false }),
    setPhone: () => send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }),
    fill: async (label, value) => {
      await waitFor(`[...document.querySelectorAll('label')].some(l => l.textContent.trim() === ${JSON.stringify(label)})`, `campo ${label}`)
      return evaluate(`(() => {
        const lab = [...document.querySelectorAll('label')].find(l => l.textContent.trim() === ${JSON.stringify(label)});
        const el = document.getElementById(lab.htmlFor);
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, ${JSON.stringify(value)});
        el.dispatchEvent(new Event('input', { bubbles: true }));
      })()`)
    },
    click: (text) =>
      evaluate(`(() => { const b = [...document.querySelectorAll('button, a')].find(b => b.textContent.trim().startsWith(${JSON.stringify(text)})); if (!b) throw new Error('sin botón ' + ${JSON.stringify(text)}); b.click() })()`),
    clickNav: (text) => evaluate(`[...document.querySelectorAll('nav a')].find(a => a.textContent.trim() === ${JSON.stringify(text)}).click()`),
    chooseFile: async (path) => {
      const { root } = await send('DOM.getDocument')
      const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: 'input[type=file]' })
      await send('DOM.setFileInputFiles', { files: [path], nodeId })
    },
    close: () => {
      ws.close()
      proc.kill()
    },
  }
}
