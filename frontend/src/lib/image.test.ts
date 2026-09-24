import { vi } from 'vitest'

import { captureFrame, prepareImage } from '@/lib/image'

interface Bitmap {
  width: number
  height: number
  close: () => void
}

function stubCanvas(blobResult: Blob | null = new Blob(['jpg'], { type: 'image/jpeg' })) {
  const drawImage = vi.fn()
  const canvas = {
    width: 0,
    height: 0,
    getContext: vi.fn(() => ({ drawImage })),
    toBlob: vi.fn((callback: (b: Blob | null) => void) => callback(blobResult)),
  }
  const realCreate = document.createElement.bind(document)
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) =>
    tag === 'canvas' ? (canvas as unknown as HTMLCanvasElement) : realCreate(tag),
  )
  return { canvas, drawImage }
}

function stubBitmap(width: number, height: number) {
  const bitmap: Bitmap = { width, height, close: vi.fn() }
  vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue(bitmap))
  return bitmap
}

afterEach(() => vi.restoreAllMocks())

describe('prepareImage', () => {
  it('reduce una foto grande a 1280 px de lado mayor y la comprime a JPEG', async () => {
    const bitmap = stubBitmap(4000, 3000)
    const { canvas } = stubCanvas()

    const result = await prepareImage(new Blob([new Uint8Array(6_000_000)], { type: 'image/jpeg' }))

    expect(canvas.width).toBe(1280)
    expect(canvas.height).toBe(960)
    expect(canvas.toBlob).toHaveBeenCalledWith(expect.any(Function), 'image/jpeg', 0.85)
    expect(result.type).toBe('image/jpeg')
    expect(bitmap.close).toHaveBeenCalled()
  })

  it('deja intacta una imagen pequeña de formato válido', async () => {
    stubBitmap(800, 600)
    const { canvas } = stubCanvas()
    const original = new Blob(['x'.repeat(1000)], { type: 'image/png' })

    expect(await prepareImage(original)).toBe(original)
    expect(canvas.toBlob).not.toHaveBeenCalled()
  })

  it('convierte a JPEG una imagen pequeña de formato no admitido', async () => {
    stubBitmap(800, 600)
    const { canvas } = stubCanvas()

    const result = await prepareImage(new Blob(['x'], { type: 'image/gif' }))

    expect(canvas.toBlob).toHaveBeenCalled()
    expect(result.type).toBe('image/jpeg')
  })

  it('devuelve la original si el navegador no puede decodificarla', async () => {
    vi.stubGlobal('createImageBitmap', vi.fn().mockRejectedValue(new Error('corrupta')))
    const original = new Blob(['x'], { type: 'image/jpeg' })

    expect(await prepareImage(original)).toBe(original)
  })

  it('devuelve la original si el navegador no tiene createImageBitmap', async () => {
    vi.stubGlobal('createImageBitmap', undefined)
    const original = new Blob(['x'], { type: 'image/jpeg' })

    expect(await prepareImage(original)).toBe(original)
  })

  it('devuelve la original si no hay contexto 2D', async () => {
    stubBitmap(4000, 3000)
    const { canvas } = stubCanvas()
    canvas.getContext.mockReturnValue(null as never)
    const original = new Blob([new Uint8Array(6_000_000)], { type: 'image/jpeg' })

    expect(await prepareImage(original)).toBe(original)
  })

  it('propaga el fallo si la compresión no produce imagen', async () => {
    const bitmap = stubBitmap(4000, 3000)
    stubCanvas(null)

    await expect(
      prepareImage(new Blob([new Uint8Array(6_000_000)], { type: 'image/jpeg' })),
    ).rejects.toThrow('No se pudo procesar la imagen')
    expect(bitmap.close).toHaveBeenCalled()
  })
})

describe('captureFrame', () => {
  it('congela el cuadro actual del video en un JPEG', async () => {
    const { canvas, drawImage } = stubCanvas()
    const video = { videoWidth: 640, videoHeight: 480 } as HTMLVideoElement

    const blob = await captureFrame(video)

    expect(canvas.width).toBe(640)
    expect(canvas.height).toBe(480)
    expect(drawImage).toHaveBeenCalledWith(video, 0, 0, 640, 480)
    expect(blob.type).toBe('image/jpeg')
  })

  it('falla con un mensaje claro si la cámara aún no entrega imagen', async () => {
    const video = { videoWidth: 0, videoHeight: 0 } as HTMLVideoElement

    await expect(captureFrame(video)).rejects.toThrow('La cámara aún no está lista')
  })

  it('falla si no hay contexto 2D', async () => {
    const { canvas } = stubCanvas()
    canvas.getContext.mockReturnValue(null as never)

    await expect(
      captureFrame({ videoWidth: 10, videoHeight: 10 } as HTMLVideoElement),
    ).rejects.toThrow('No se pudo capturar la imagen')
  })
})
