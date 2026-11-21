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

const PHOTO = new Blob(['jpeg'], { type: 'image/jpeg' })

function record(n: number, overrides: Record<string, unknown> = {}) {
  return makeClassification({
    id: `c${n}`,
    image_url: `/api/v1/classifications/c${n}/image`,
    item: { code: `item${n}`, display_name: `Residuo ${n}` },
    ...overrides,
  })
}

describe('Historial (RF-16, RF-17)', () => {
  beforeEach(() => startSession())

  it('lista las clasificaciones con objeto, bolsa, confianza y miniatura protegida', async () => {
    const { fetchMock } = mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({
        json: {
          items: [record(1), record(2, { confidence_band: 'medium', confidence: 0.7 })],
          total: 2,
          limit: 10,
          offset: 0,
        },
      }),
      'GET /api/v1/classifications/c1/image': () => ({ blob: PHOTO }),
      'GET /api/v1/classifications/c2/image': () => ({ blob: PHOTO }),
    })
    renderApp('/historial')

    const list = await screen.findByRole('list', { name: 'Clasificaciones' })
    const rows = within(list).getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(within(rows[0]!).getByText('Residuo 1')).toBeInTheDocument()
    expect(within(rows[0]!).getByText('Bolsa blanca')).toBeInTheDocument()
    expect(within(rows[0]!).getByText(/Confianza alta · 92 %/)).toBeInTheDocument()
    expect(within(rows[1]!).getByText(/Confianza media · 70 %/)).toBeInTheDocument()
    expect(screen.getByText('2 clasificaciones')).toBeInTheDocument()

    expect(await screen.findByRole('img', { name: 'Foto de Residuo 1' })).toBeInTheDocument()
    const photoCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/c1/image'))
    expect((photoCall![1]!.headers as Record<string, string>).Authorization).toBe('Bearer access-2')
  })

  it('sin registros muestra un estado vacío que invita a escanear', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    })
    renderApp('/historial')

    expect(await screen.findByText('Aún no has clasificado ningún residuo.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Escanear un residuo' })).toHaveAttribute(
      'href',
      '/escanear',
    )
  })

  it('«Cargar más» pide la siguiente página y desaparece al llegar al final', async () => {
    const offsets: string[] = []
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': ({ search }) => {
        const offset = Number(search.get('offset'))
        offsets.push(`${search.get('limit')}:${offset}`)
        return offset === 0
          ? { json: { items: [record(1)], total: 2, limit: 1, offset: 0 } }
          : { json: { items: [record(2)], total: 2, limit: 1, offset: 1 } }
      },
      'GET /api/v1/classifications/c1/image': () => ({ blob: PHOTO }),
      'GET /api/v1/classifications/c2/image': () => ({ blob: PHOTO }),
    })
    renderApp('/historial')

    await userEvent.click(await screen.findByRole('button', { name: 'Cargar más' }))

    expect(await screen.findByText('Residuo 2')).toBeInTheDocument()
    expect(screen.getByText('Residuo 1')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cargar más' })).not.toBeInTheDocument()
    expect(offsets).toEqual(['10:0', '10:1'])
  })

  it('si la carga falla, avisa y permite reintentar', async () => {
    let attempts = 0
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => {
        attempts += 1
        return attempts === 1 ? { status: 500, json: { detail: 'x' } } : { json: EMPTY_HISTORY }
      },
    })
    renderApp('/historial')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar tu historial')
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Aún no has clasificado ningún residuo.')).toBeInTheDocument()
  })

  it('si la foto no se puede descargar, muestra un marcador en vez de romper la lista', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({
        json: { items: [record(1)], total: 1, limit: 10, offset: 0 },
      }),
      'GET /api/v1/classifications/c1/image': () => ({ status: 404, json: { detail: 'x' } }),
    })
    renderApp('/historial')

    expect(await screen.findByText('Residuo 1')).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: 'Foto no disponible' })).toBeInTheDocument()
  })
})
