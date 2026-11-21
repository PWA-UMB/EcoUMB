import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import {
  EMPTY_HISTORY,
  makeClassification,
  mockApi,
  renderApp,
  SESSION_ROUTES,
  startSession,
} from '@/test/utils'

const JPEG = new File([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], 'foto.jpg', {
  type: 'image/jpeg',
})

const EDUCATION = {
  normative: { title: 'Resolución 2184', summary: 's', note: 'n' },
  bags: [
    {
      category: 'aprovechable',
      bag_color: 'blanca',
      description: 'd',
      educational_text: 't',
      items: [
        { code: 'botella_pet', display_name: 'Botella PET', disposal_tip: 'x' },
        { code: 'lata_aluminio', display_name: 'Lata de aluminio', disposal_tip: 'x' },
      ],
    },
    {
      category: 'organico',
      bag_color: 'verde',
      description: 'd',
      educational_text: 't',
      items: [{ code: 'cascara_fruta', display_name: 'Cáscara de fruta', disposal_tip: 'x' }],
    },
  ],
  practices: [],
}

function feedbackRoute(calls: unknown[]) {
  return ({ body }: { body: unknown }) => {
    const { item_code } = body as { item_code: string }
    calls.push(item_code)
    const names: Record<string, string> = {
      botella_pet: 'Botella PET',
      lata_aluminio: 'Lata de aluminio',
      cascara_fruta: 'Cáscara de fruta',
    }
    return {
      json: makeClassification({
        feedback: {
          item: { code: item_code, display_name: names[item_code] },
          category: { code: 'aprovechable', bag_color: 'blanca' },
          was_corrected: item_code !== 'botella_pet',
        },
      }),
    }
  }
}

async function openResult(extra: Record<string, () => { status?: number; json?: unknown }> = {}) {
  const calls: unknown[] = []
  mockApi({
    ...SESSION_ROUTES,
    'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    'POST /api/v1/classifications': () => ({ status: 201, json: makeClassification() }),
    'PUT /api/v1/classifications/c1/feedback': feedbackRoute(calls),
    'GET /api/v1/education': () => ({ json: EDUCATION }),
    ...extra,
  })
  renderApp('/escanear')
  await userEvent.upload(await screen.findByLabelText('Elegir foto de la galería'), JPEG)
  await userEvent.click(await screen.findByRole('button', { name: 'Clasificar' }))
  await screen.findByRole('heading', { name: 'Botella plástica PET' })
  return calls
}

beforeEach(() => startSession())

describe('Confirmar o corregir el resultado (RF-29, RF-30)', () => {
  it('confirma el resultado con un solo toque y agradece', async () => {
    const calls = await openResult()

    await userEvent.click(screen.getByRole('button', { name: 'Sí, es correcto' }))

    expect(await screen.findByText('Gracias por confirmar el resultado.')).toBeInTheDocument()
    expect(calls).toEqual(['botella_pet'])
  })

  it('avisa que la respuesta y la foto pueden usarse para mejorar el modelo', async () => {
    await openResult()

    expect(screen.getByText(/pueden usarse para mejorar el modelo/)).toBeInTheDocument()
  })

  it('permite corregir eligiendo el objeto real entre los del catálogo, agrupados por bolsa', async () => {
    const calls = await openResult()

    await userEvent.click(screen.getByRole('button', { name: 'No, corregir' }))
    const white = await screen.findByRole('list', { name: 'Objetos de la bolsa blanca' })
    expect(within(white).getByRole('button', { name: 'Lata de aluminio' })).toBeInTheDocument()
    expect(
      within(screen.getByRole('list', { name: 'Objetos de la bolsa verde' })).getByRole('button', {
        name: 'Cáscara de fruta',
      }),
    ).toBeInTheDocument()
    await userEvent.click(within(white).getByRole('button', { name: 'Lata de aluminio' }))

    expect(
      await screen.findByText('Gracias. Guardamos que era: Lata de aluminio.'),
    ).toBeInTheDocument()
    expect(calls).toEqual(['lata_aluminio'])
  })

  it('«Cancelar» vuelve a las dos opciones sin enviar nada', async () => {
    const calls = await openResult()

    await userEvent.click(screen.getByRole('button', { name: 'No, corregir' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))

    expect(screen.getByRole('button', { name: 'Sí, es correcto' })).toBeInTheDocument()
    expect(calls).toEqual([])
  })

  it('permite cambiar la respuesta ya enviada', async () => {
    const calls = await openResult()
    await userEvent.click(screen.getByRole('button', { name: 'Sí, es correcto' }))

    await userEvent.click(await screen.findByRole('button', { name: 'Cambiar mi respuesta' }))
    await userEvent.click(
      within(await screen.findByRole('list', { name: 'Objetos de la bolsa blanca' })).getByRole(
        'button',
        { name: 'Lata de aluminio' },
      ),
    )

    expect(await screen.findByText(/Guardamos que era: Lata de aluminio/)).toBeInTheDocument()
    expect(calls).toEqual(['botella_pet', 'lata_aluminio'])
  })

  it('si no se puede guardar, lo dice y deja reintentar', async () => {
    await openResult({
      'PUT /api/v1/classifications/c1/feedback': () => ({ status: 500, json: { detail: 'x' } }),
    })

    await userEvent.click(screen.getByRole('button', { name: 'Sí, es correcto' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar tu respuesta')
    expect(screen.getByRole('button', { name: 'Sí, es correcto' })).toBeEnabled()
  })

  it('si la lista de objetos no carga, lo dice', async () => {
    await openResult({ 'GET /api/v1/education': () => ({ status: 500, json: { detail: 'x' } }) })

    await userEvent.click(screen.getByRole('button', { name: 'No, corregir' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar la lista')
  })
})
