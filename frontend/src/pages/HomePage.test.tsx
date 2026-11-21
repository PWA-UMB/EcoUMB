import { act, screen, within } from '@testing-library/react'
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

describe('Inicio y navegación (Sprint 2)', () => {
  beforeEach(() => startSession())

  it('muestra las últimas clasificaciones y un acceso directo a escanear', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({
        json: { items: [makeClassification()], total: 1, limit: 3, offset: 0 },
      }),
      'GET /api/v1/classifications/c1/image': () => ({
        blob: new Blob(['x'], { type: 'image/jpeg' }),
      }),
    })
    renderApp('/')

    const list = await screen.findByRole('list', { name: 'Últimas clasificaciones' })
    expect(within(list).getByText('Botella plástica PET')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Escanear un residuo' })).toHaveAttribute(
      'href',
      '/escanear',
    )
    expect(screen.getByRole('link', { name: 'Ver todo' })).toHaveAttribute('href', '/historial')
  })

  it('sin clasificaciones lo dice y no muestra «Ver todo»', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    })
    renderApp('/')

    expect(await screen.findByText('Aún no has clasificado ningún residuo.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ver todo' })).not.toBeInTheDocument()
  })

  it('la barra de navegación lleva a Escanear, Historial y Perfil', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    })
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Principal' })

    await userEvent.click(within(nav).getByRole('link', { name: 'Escanear' }))
    expect(await screen.findByRole('heading', { name: 'Escanear un residuo' })).toBeInTheDocument()

    await userEvent.click(within(nav).getByRole('link', { name: 'Historial' }))
    expect(await screen.findByRole('heading', { name: 'Historial' })).toBeInTheDocument()

    await userEvent.click(within(nav).getByRole('link', { name: 'Perfil' }))
    expect(await screen.findByRole('heading', { name: 'Mi perfil' })).toBeInTheDocument()

    await userEvent.click(within(nav).getByRole('link', { name: 'Inicio' }))
    expect(await screen.findByRole('heading', { name: 'Ana Pérez' })).toBeInTheDocument()
  })

  it('ofrece instalar la aplicación cuando el navegador la considera instalable', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    })
    renderApp('/')
    await screen.findByRole('heading', { name: 'Ana Pérez' })
    expect(screen.queryByRole('button', { name: 'Instalar la aplicación' })).not.toBeInTheDocument()

    const prompt = vi.fn().mockResolvedValue(undefined)
    const event = Object.assign(new Event('beforeinstallprompt', { cancelable: true }), {
      prompt,
      userChoice: Promise.resolve({ outcome: 'accepted' }),
    })
    act(() => {
      window.dispatchEvent(event)
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Instalar la aplicación' }))

    expect(event.defaultPrevented).toBe(true)
    expect(prompt).toHaveBeenCalledOnce()
    expect(screen.queryByRole('button', { name: 'Instalar la aplicación' })).not.toBeInTheDocument()
  })

  it('oculta el botón de instalar cuando la app ya quedó instalada', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
    })
    renderApp('/')
    await screen.findByRole('heading', { name: 'Ana Pérez' })

    act(() => {
      window.dispatchEvent(
        Object.assign(new Event('beforeinstallprompt', { cancelable: true }), {
          prompt: vi.fn(),
          userChoice: Promise.resolve({ outcome: 'dismissed' }),
        }),
      )
    })
    expect(
      await screen.findByRole('button', { name: 'Instalar la aplicación' }),
    ).toBeInTheDocument()

    act(() => {
      window.dispatchEvent(new Event('appinstalled'))
    })

    expect(screen.queryByRole('button', { name: 'Instalar la aplicación' })).not.toBeInTheDocument()
  })
})
