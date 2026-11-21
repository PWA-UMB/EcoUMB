// Recorre en la PWA REAL (Docker compose) lo nuevo del Sprint 3: el modelo de IA v1 clasificando fotos reales
// de TrashNet (del conjunto de TEST, que el modelo no vio al entrenar) y el módulo educativo «Aprende».
// Uso:  node scripts/capture_sprint3.mjs [URL_PWA] [URL_API] [carpeta_salida]
// Requiere: `docker compose up -d`, ml/data/raw/dataset-resized (ver ml/models/v1/MODEL_CARD.md) y Edge o Chrome.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

import { launch } from './lib/cdp.mjs'

const PWA = (process.argv[2] ?? 'http://localhost:5173').replace(/\/$/, '')
const API = (process.argv[3] ?? 'http://localhost:8000').replace(/\/$/, '')
const OUT = process.argv[4] ?? 'docs/evidencias/capturas'
const PHOTOS = resolve('ml/data/raw/dataset-resized')
mkdirSync(OUT, { recursive: true })

// Una foto real de cada material, tomada del conjunto de test (ver ml/models/v1/splits.json).
const test = JSON.parse(readFileSync('ml/data/splits.json', 'utf8')).test
const MATERIALS = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']
const samples = MATERIALS.map((name, index) => ({ name, file: test.find(([, label]) => label === index)[0] }))

const browser = await launch({ port: 9335, pwa: PWA, outDir: OUT })
const { evaluate, waitFor, bodyHas, shot, goto, fill, click, clickNav, chooseFile, setDesktop, setPhone } = browser
process.on('unhandledRejection', (error) => {
  console.error(error)
  browser.close()
  process.exit(1)
})

const results = []
try {
  await browser.send('Page.enable')
  await browser.send('Network.enable')
  await browser.send('DOM.enable')

  const email = `sprint3.${Date.now()}@umb.edu.co`
  const password = 'Clave-Segura-2026'
  const reg = await fetch(`${API}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: 'Laura Gómez' }),
  })
  if (reg.status !== 201) throw new Error(`No se pudo crear la cuenta de prueba: HTTP ${reg.status}`)

  await setPhone()
  await goto('/login')
  await fill('Correo electrónico', email)
  await fill('Contraseña', password)
  await click('Iniciar sesión')
  await waitFor(`location.pathname === '/'`, 'Home')

  await clickNav('Escanear')
  await waitFor(bodyHas('Elegir de la galería'), 'pantalla Escanear')
  for (const [index, { name, file }] of samples.entries()) {
    if (index > 0) {
      await click('Escanear otro residuo')
      await waitFor(bodyHas('Elegir de la galería'), 'volver a elegir')
    }
    await chooseFile(join(PHOTOS, file))
    await waitFor(`!!document.querySelector('img[alt="Vista previa del residuo"]')`, `vista previa ${name}`)
    await click('Clasificar')
    await waitFor(`!!document.querySelector('article[aria-labelledby=result-title]')`, `resultado ${name}`)
    const text = await evaluate(`document.querySelector('article[aria-labelledby=result-title]').innerText.replace(/\\n+/g, ' | ')`)
    results.push(`foto real de «${name}» (${file}): ${text}`)
    await shot(`s3-0${index + 1}-modelo-${name}-movil.png`)
  }

  await clickNav('Historial')
  await waitFor(`document.querySelectorAll('ul[aria-label=Clasificaciones] li').length >= ${samples.length}`, 'historial')
  await waitFor(`[...document.querySelectorAll('ul[aria-label=Clasificaciones] img')].every(i => i.alt.startsWith('Foto de'))`, 'miniaturas')
  await shot('s3-07-historial-modelo-movil.png')

  // --- Módulo educativo (RF-26, RF-27, RF-28) ---
  await clickNav('Aprende')
  await waitFor(`location.pathname === '/aprende' && ${bodyHas('Buenas prácticas')}`, 'guía educativa')
  await shot('s3-08-aprende-movil.png')
  await setDesktop()
  await sleep(300)
  await shot('s3-09-aprende-escritorio.png')
  await evaluate('window.scrollTo(0, document.body.scrollHeight)')
  await shot('s3-10-aprende-buenas-practicas-escritorio.png')

  const header = `# Solicitudes a la API en el recorrido del Sprint 3  |  ${new Date().toISOString().slice(0, 16).replace('T', ' ')}\n# PWA: ${PWA}\n\n`
  writeFileSync(join(OUT, '..', 'red-navegador-sprint3.txt'), header + browser.apiLog.join('\n') + '\n')
  writeFileSync(
    join(OUT, '..', 'sprint3-resultados-modelo.txt'),
    ['# Respuestas del modelo v1 a una foto REAL de cada material (conjunto de test de TrashNet), vistas en la PWA', '', ...results, ''].join('\n'),
  )
  console.log('\n' + results.join('\n'))
} finally {
  browser.close()
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}
