import { ApiError } from '@/lib/api'

/** Traduce errores de la API a mensajes comprensibles para personas sin formación técnica. */
export function describeAuthError(error: unknown, context: 'login' | 'register'): string {
  if (!(error instanceof ApiError)) return 'Ocurrió un error inesperado. Intenta de nuevo.'
  switch (error.status) {
    case 0:
      return error.message
    case 401:
      return 'El correo o la contraseña no son correctos.'
    case 409:
      return 'Ya existe una cuenta con este correo. Inicia sesión.'
    case 422:
      return context === 'register'
        ? 'Revisa los datos ingresados e intenta de nuevo.'
        : 'Revisa tu correo y contraseña.'
    case 429:
      return 'Demasiados intentos. Espera un minuto e intenta de nuevo.'
    default:
      return error.status >= 500
        ? 'El servicio no está disponible en este momento. Intenta más tarde.'
        : error.message
  }
}
