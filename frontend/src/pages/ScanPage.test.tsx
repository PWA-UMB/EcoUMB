import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import {
  EMPTY_HISTORY,
  makeClassification,
  mockApi,
  renderApp,
  SESSION_ROUTES,
  startSession,
} from '@/test/utils'

vi.mock('@/lib/image', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/image')>()),
  captureFrame: vi.fn(async () => new Blob(['frame'], { type: 'image/jpeg' })),
}))

const JPEG = new File([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], 'foto.jpg', {
  type: 'image/jpeg',
})

function routes(classify: () => { status?: number; json?: unknown }) {
  return {
    ...SESSION_ROUTES,
    'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    'POST /api/v1/classifications': classify,
  }
}

async function openScanWithPhoto() {
  renderApp('/escanear')
  await userEvent.upload(await screen.findByLabelText('Elegir foto de la galería'), JPEG)
  return screen.findByRole('img', { name: 'Vista previa del residuo' })
}

function fakeCamera() {
  const stop = vi.fn()
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] })
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia } })
  return { stop, getUserMedia }
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'mediaDevices')
})

describe('Escanear: galería (RF-10)', () => {
  beforeEach(() => startSession())

  it('elige una foto, muestra la vista previa y la clasifica con el token del usuario', async () => {
    const { fetchMock } = mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    await openScanWithPhoto()

    await userEvent.click(screen.getByRole('button', { name: 'Clasificar' }))

    expect(await screen.findByRole('heading', { name: 'Botella plástica PET' })).toBeInTheDocument()
    expect(screen.getByText('Bolsa blanca')).toBeInTheDocument()
    expect(screen.getByText(/Aplástala/)).toBeInTheDocument()
    expect(screen.getByText(/Resultado simulado/)).toBeInTheDocument()

    const upload = fetchMock.mock.calls.find(
      ([, init]) => init?.method === 'POST' && init.body instanceof FormData,
    )
    const [, init] = upload!
    expect((init!.headers as Record<string, string>).Authorization).toBe('Bearer access-2')
    expect((init!.headers as Record<string, string>)['Content-Type']).toBeUndefined()
    const sent = (init!.body as FormData).get('image') as File
    expect(sent.name).toBe('residuo.jpg')
  })

  it('con el modelo real indica la versión y su alcance, y no dice «simulado»', async () => {
    mockApi(
      routes(() => ({
        status: 201,
        json: makeClassification({ simulated: false, model_version: 'v1' }),
      })),
    )
    await openScanWithPhoto()

    await userEvent.click(screen.getByRole('button', { name: 'Clasificar' }))

    expect(await screen.findByText(/· Modelo v1/)).toBeInTheDocument()
    expect(screen.getByText(/aún no cubre todos los objetos del catálogo/)).toBeInTheDocument()
    expect(screen.queryByText(/Resultado simulado/)).not.toBeInTheDocument()
  })

  it('con confianza baja no afirma un residuo y ofrece las opciones más probables', async () => {
    mockApi(
      routes(() => ({
        status: 201,
        json: makeClassification({ confidence: 0.4, confidence_band: 'low' }),
      })),
    )
    await openScanWithPhoto()

    await userEvent.click(screen.getByRole('button', { name: 'Clasificar' }))

    expect(
      await screen.findByRole('heading', { name: /No logramos identificar/ }),
    ).toBeInTheDocument()
    expect(screen.getByText('Lata de aluminio')).toBeInTheDocument()
    expect(screen.queryByText(/Aplástala/)).not.toBeInTheDocument()
  })

  it('«Escanear otro residuo» vuelve a la selección de foto', async () => {
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    await openScanWithPhoto()
    await userEvent.click(screen.getByRole('button', { name: 'Clasificar' }))

    await userEvent.click(await screen.findByRole('button', { name: 'Escanear otro residuo' }))

    expect(screen.getByRole('button', { name: 'Abrir la cámara' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Elegir de la galería' })).toBeInTheDocument()
  })

  it('«Elegir otra foto» descarta la vista previa', async () => {
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    await openScanWithPhoto()

    await userEvent.click(screen.getByRole('button', { name: 'Elegir otra foto' }))

    expect(screen.queryByRole('img', { name: 'Vista previa del residuo' })).not.toBeInTheDocument()
    expect(URL.revokeObjectURL).toHaveBeenCalled()
  })

  it.each([
    [413, 'demasiado grande'],
    [415, 'Formato no admitido'],
    [422, 'no es válida'],
    [429, 'muchas clasificaciones'],
    [503, 'no está disponible'],
    [500, 'no está disponible'],
  ])('traduce el error %i a un mensaje claro y permite reintentar', async (status, expected) => {
    mockApi(routes(() => ({ status, json: { detail: 'x' } })))
    await openScanWithPhoto()

    await userEvent.click(screen.getByRole('button', { name: 'Clasificar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(expected)
    expect(screen.getByRole('button', { name: 'Clasificar' })).toBeEnabled()
  })

  it('informa cuando no hay conexión con el servidor', async () => {
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    await openScanWithPhoto()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await userEvent.click(screen.getByRole('button', { name: 'Clasificar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar')
  })

  it('rechaza en el cliente un archivo que no es una imagen admitida', async () => {
    const { fetchMock } = mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    renderApp('/escanear')
    const user = userEvent.setup({ applyAccept: false })

    await user.upload(
      await screen.findByLabelText('Elegir foto de la galería'),
      new File(['%PDF'], 'doc.pdf', { type: 'application/pdf' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Formato no admitido')
    expect(fetchMock.mock.calls.some(([, init]) => init?.body instanceof FormData)).toBe(false)
  })
})

describe('Escanear: cámara (RF-09)', () => {
  beforeEach(() => startSession())

  it('abre la cámara, toma la foto y libera el hardware', async () => {
    const { stop, getUserMedia } = fakeCamera()
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    renderApp('/escanear')

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir la cámara' }))
    expect(getUserMedia).toHaveBeenCalledWith({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    })
    const capture = await screen.findByRole('button', { name: 'Tomar foto' })
    await waitFor(() => expect(capture).toBeEnabled())
    await userEvent.click(capture)

    expect(await screen.findByRole('img', { name: 'Vista previa del residuo' })).toBeInTheDocument()
    expect(stop).toHaveBeenCalled()
  })

  it('cancelar cierra la cámara y regresa a las opciones', async () => {
    const { stop } = fakeCamera()
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    renderApp('/escanear')

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir la cámara' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))

    expect(stop).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Elegir de la galería' })).toBeInTheDocument()
  })

  it('si el usuario niega el permiso, lo explica y deja la galería disponible', async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException('denied', 'NotAllowedError'))
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia },
    })
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    renderApp('/escanear')

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir la cámara' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No diste permiso')
    expect(screen.getByRole('button', { name: 'Elegir de la galería' })).toBeInTheDocument()
  })

  it('explica cuando el dispositivo no tiene cámara', async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException('none', 'NotFoundError'))
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia },
    })
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    renderApp('/escanear')

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir la cámara' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se encontró una cámara')
  })

  it('si el navegador no soporta la cámara, lo indica', async () => {
    mockApi(routes(() => ({ status: 201, json: makeClassification() })))
    renderApp('/escanear')

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir la cámara' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('no permite usar la cámara')
  })
})
