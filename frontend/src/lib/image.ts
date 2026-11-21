/** Utilidades de imagen del navegador (RF-09, RF-10). */

const MAX_SIDE = 1280
const JPEG_QUALITY = 0.85
/** Formatos que el servidor acepta (RF-10). */
export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
/** Por debajo de este tamaño, y con formato válido, la foto se envía tal cual. */
const KEEP_AS_IS_BYTES = 1_500_000

function toBlob(canvas: HTMLCanvasElement, type: string, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('No se pudo procesar la imagen'))),
      type,
      quality,
    )
  })
}

/**
 * Reduce la foto a 1280 px de lado mayor y la comprime a JPEG. Una foto de celular pesa 4-12 MB: sin este
 * paso superaría el límite del servidor (5 MB) y tardaría en subir (RNF-01). Si el navegador no puede
 * decodificarla, se devuelve la original y el servidor decide.
 */
export async function prepareImage(source: Blob): Promise<Blob> {
  if (typeof createImageBitmap !== 'function') return source
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(source)
  } catch {
    return source
  }
  try {
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
    if (scale === 1 && ACCEPTED_TYPES.includes(source.type) && source.size <= KEEP_AS_IS_BYTES)
      return source
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    const context = canvas.getContext('2d')
    if (!context) return source
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    return await toBlob(canvas, 'image/jpeg', JPEG_QUALITY)
  } finally {
    bitmap.close()
  }
}

/** Congela el cuadro actual de un `<video>` en una imagen JPEG. */
export async function captureFrame(video: HTMLVideoElement): Promise<Blob> {
  const width = video.videoWidth
  const height = video.videoHeight
  if (!width || !height) throw new Error('La cámara aún no está lista')
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('No se pudo capturar la imagen')
  context.drawImage(video, 0, 0, width, height)
  return toBlob(canvas, 'image/jpeg', 0.9)
}
