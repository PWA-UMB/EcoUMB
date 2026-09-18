import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { useAuthStore } from '@/stores/authStore'
import { ANA, mockApi, renderApp, TOKENS } from '@/test/utils'

async function fillAndSubmit(email: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Correo electrónico'), email)
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
}

describe('Inicio de sesión (S1-08)', () => {
  it('valida el formulario antes de llamar al servidor', async () => {
    const { fetchMock } = mockApi({})
    renderApp('/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Iniciar sesión' }))

    expect(await screen.findByText('Ingresa tu correo')).toBeInTheDocument()
    expect(screen.getByText('Ingresa tu contraseña')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('inicia sesión, llega al Home y guarda solo el refresh token', async () => {
    mockApi({
      'POST /api/v1/auth/login': () => ({ json: TOKENS }),
      'GET /api/v1/users/me': () => ({ json: ANA }),
    })
    renderApp('/login')

    await screen.findByRole('button', { name: 'Iniciar sesión' })
    await fillAndSubmit('ana@umb.edu.co', 'Clave-Segura-2026')

    expect(await screen.findByRole('heading', { name: 'Ana Pérez' })).toBeInTheDocument()
    const stored = JSON.parse(localStorage.getItem('ecoumb.session') ?? '{}')
    expect(stored.state).toEqual({ refreshToken: 'refresh-1' }) // el access token NO se persiste
  })

  it('muestra un mensaje claro ante credenciales inválidas y se queda en el login', async () => {
    mockApi({
      'POST /api/v1/auth/login': () => ({
        status: 401,
        json: { detail: 'Credenciales inválidas' },
      }),
    })
    renderApp('/login')

    await screen.findByRole('button', { name: 'Iniciar sesión' })
    await fillAndSubmit('ana@umb.edu.co', 'incorrecta1')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El correo o la contraseña no son correctos.',
    )
    expect(screen.getByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument()
  })

  it('informa cuando no hay conexión con el servidor', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', fetchMock)
    renderApp('/login')

    await screen.findByRole('button', { name: 'Iniciar sesión' })
    await fillAndSubmit('ana@umb.edu.co', 'Clave-Segura-2026')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo conectar con el servidor',
    )
  })

  it('informa cuando se superó el límite de intentos (429)', async () => {
    mockApi({ 'POST /api/v1/auth/login': () => ({ status: 429, json: { detail: 'x' } }) })
    renderApp('/login')

    await screen.findByRole('button', { name: 'Iniciar sesión' })
    await fillAndSubmit('ana@umb.edu.co', 'Clave-Segura-2026')

    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos')
  })
})

describe('Sesión persistente (S1-08)', () => {
  it('recupera la sesión al recargar usando el refresh token guardado', async () => {
    useAuthStore.setState({ refreshToken: 'refresh-1' })
    mockApi({
      'POST /api/v1/auth/refresh': () => ({ json: { access_token: 'access-2', expires_in: 900 } }),
      'GET /api/v1/users/me': () => ({ json: ANA }),
    })

    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Ana Pérez' })).toBeInTheDocument()
  })

  it('si el refresh token ya no sirve, lo descarta y pide iniciar sesión', async () => {
    useAuthStore.setState({ refreshToken: 'vencido' })
    mockApi({
      'POST /api/v1/auth/refresh': () => ({
        status: 401,
        json: { detail: 'Token inválido o expirado' },
      }),
    })

    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument()
    expect(useAuthStore.getState().refreshToken).toBeNull()
  })

  it('sin sesión, una ruta protegida redirige al login', async () => {
    mockApi({})
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument()
  })

  it('cerrar sesión vuelve al login y borra el refresh token', async () => {
    useAuthStore.setState({ refreshToken: 'refresh-1' })
    mockApi({
      'POST /api/v1/auth/refresh': () => ({ json: { access_token: 'access-2', expires_in: 900 } }),
      'GET /api/v1/users/me': () => ({ json: ANA }),
    })
    renderApp('/')

    await userEvent.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))

    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument()
    await waitFor(() => expect(useAuthStore.getState().refreshToken).toBeNull())
  })

  it('con sesión activa, /login redirige al Home', async () => {
    useAuthStore.setState({ refreshToken: 'refresh-1' })
    mockApi({
      'POST /api/v1/auth/refresh': () => ({ json: { access_token: 'access-2', expires_in: 900 } }),
      'GET /api/v1/users/me': () => ({ json: ANA }),
    })

    renderApp('/login')

    expect(await screen.findByRole('heading', { name: 'Ana Pérez' })).toBeInTheDocument()
  })
})
