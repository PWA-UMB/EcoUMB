import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { App } from '@/app/App'

export interface MockResponse {
  status?: number
  json?: unknown
}
export interface MockCall {
  headers: Record<string, string>
  body: unknown
}
type Handler = (call: MockCall) => MockResponse | Promise<MockResponse>

/** Sustituye `fetch`. Las rutas se indican como `"METODO /ruta"`; una ruta sin mock falla la prueba. */
export function mockApi(routes: Record<string, Handler>) {
  const calls: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${new URL(String(input)).pathname}`
    calls.push(key)
    const handler = routes[key]
    if (!handler) throw new Error(`Solicitud sin mock: ${key}`)
    const { status = 200, json = null } = await handler({
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    })
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
