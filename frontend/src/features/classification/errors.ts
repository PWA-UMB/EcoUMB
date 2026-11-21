import { ApiError } from '@/lib/api'

/** Mensajes comprensibles para los errores de la clasificación (RNF-09, RNF-11). */
export function describeClassifyError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Ocurrió un error inesperado. Intenta de nuevo.'
  switch (error.status) {
    case 0:
      return error.message
    case 413:
      return 'La foto es demasiado grande. Intenta con otra.'
    case 415:
      return 'Formato no admitido. Usa una imagen JPEG, PNG o WebP.'
    case 422:
      return 'La imagen no es válida. Intenta con otra foto.'
    case 429:
      return 'Hiciste muchas clasificaciones seguidas. Espera un momento e intenta de nuevo.'
    case 503:
      return 'El servicio de clasificación no está disponible por ahora.'
    default:
      return error.status >= 500
        ? 'El servicio no está disponible en este momento. Intenta más tarde.'
        : error.message
  }
}
