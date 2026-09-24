import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { App } from '@/app/App'
import { useAuthStore } from '@/stores/authStore'

export interface MockResponse {
  status?: number
  json?: unknown
  /** Respuesta binaria (foto protegida). */
  blob?: Blob
}
export interface MockCall {
  headers: Record<string, string>
  /** JSON ya interpretado, o el `FormData` cuando la solicitud sube un archivo. */
  body: unknown
  search: URLSearchParams
}
type Handler = (call: MockCall) => MockResponse | Promise<MockResponse>

function parseBody(body: BodyInit | null | undefined): unknown {
  if (!body) return undefined
  return body instanceof FormData ? body : JSON.parse(String(body))
}

/** Sustituye `fetch`. Las rutas se indican como `"METODO /ruta"`; una ruta sin mock falla la prueba. */
export function mockApi(routes: Record<string, Handler>) {
  const calls: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input))
    const key = `${init?.method ?? 'GET'} ${url.pathname}`
    calls.push(key)
    const handler = routes[key]
    if (!handler) throw new Error(`Solicitud sin mock: ${key}`)
    const {
      status = 200,
      json = null,
      blob,
    } = await handler({
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: parseBody(init?.body),
      search: url.searchParams,
    })
    if (blob) return new Response(blob, { status, headers: { 'Content-Type': blob.type } })
    return new Response(json === null ? null : JSON.stringify(json), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock }
}

export function renderApp(path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={[path]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

export const ANA = {
  id: '5d1f0a52-0000-4000-8000-000000000001',
  email: 'ana@umb.edu.co',
  full_name: 'Ana Pérez',
  role: 'user',
  total_points: 0,
  level: 1,
} as const

export const TOKENS = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  token_type: 'bearer',
  expires_in: 900,
} as const

export const EMPTY_HISTORY = { items: [], total: 0, limit: 10, offset: 0 } as const

/** Sesión ya iniciada: el refresh token guardado se canjea y se carga el usuario. */
export const SESSION_ROUTES = {
  'POST /api/v1/auth/refresh': () => ({ json: { access_token: 'access-2', expires_in: 900 } }),
  'GET /api/v1/users/me': () => ({ json: ANA }),
} as const

export function makeClassification(overrides: Record<string, unknown> = {}) {
  return {
    id: 'c1',
    created_at: '2026-09-18T15:30:00Z',
    simulated: true,
    model_version: null,
    confidence: 0.92,
    confidence_band: 'high',
    item: { code: 'botella_pet', display_name: 'Botella plástica PET' },
    category: { code: 'aprovechable', bag_color: 'blanca' },
    message: 'Va en la bolsa blanca: es aprovechable.',
    tip: 'Aplástala y ponle la tapa.',
    points_awarded: 0,
    top3: [
      {
        code: 'botella_pet',
        display_name: 'Botella plástica PET',
        bag_color: 'blanca',
        confidence: 0.92,
      },
      { code: 'lata', display_name: 'Lata de aluminio', bag_color: 'blanca', confidence: 0.05 },
    ],
    image_url: '/api/v1/classifications/c1/image',
    feedback: null,
    ...overrides,
  }
}

/** Simula que el usuario ya había iniciado sesión: `bootstrap` canjeará este refresh token. */
export function startSession() {
  useAuthStore.setState({ refreshToken: 'refresh-1' })
}
