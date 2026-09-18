/** Cliente HTTP mínimo con JWT (SAD §3.1). Renueva el access token una vez ante un 401. */

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  /** `status` 0 = no hubo respuesta (red caída, CORS, servidor apagado). */
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface AuthHooks {
  getAccessToken: () => string | null
  /** Devuelve un access token nuevo, o `null` si la sesión ya no es recuperable. */
  refreshAccessToken: () => Promise<string | null>
}

let hooks: AuthHooks = { getAccessToken: () => null, refreshAccessToken: async () => null }

/** Lo llama el store de sesión; evita una dependencia circular api ↔ store. */
export function configureAuth(next: AuthHooks): void {
  hooks = next
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  /** `false` para endpoints públicos (login, registro, refresh). */
  auth?: boolean
}

const GENERIC_ERROR = 'Ocurrió un error inesperado. Intenta de nuevo.'

function messageFrom(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const { detail } = payload as { detail: unknown }
    if (typeof detail === 'string') return detail
  }
  return GENERIC_ERROR
}

export async function request<T>(
  path: string,
  { method = 'GET', body, auth = true }: RequestOptions = {},
  retried = false,
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = auth ? hooks.getAccessToken() : null
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor. Revisa tu conexión.')
  }

  if (response.status === 401 && auth && !retried) {
    const fresh = await hooks.refreshAccessToken()
    if (fresh) return request<T>(path, { method, body, auth }, true)
  }

  const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, messageFrom(payload))
  return payload as T
}
