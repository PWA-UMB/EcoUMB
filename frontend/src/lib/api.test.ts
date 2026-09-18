import { authApi } from '@/features/auth/authApi'
import { ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { ANA, mockApi } from '@/test/utils'

describe('cliente HTTP', () => {
  it('ante un 401 renueva el access token una vez y repite la solicitud', async () => {
    useAuthStore.setState({ accessToken: 'viejo', refreshToken: 'refresh-1' })
    const { calls } = mockApi({
      'POST /api/v1/auth/refresh': () => ({ json: { access_token: 'nuevo', expires_in: 900 } }),
      'GET /api/v1/users/me': ({ headers }) =>
        headers.Authorization === 'Bearer nuevo'
          ? { json: ANA }
          : { status: 401, json: { detail: 'Token inválido o expirado' } },
    })

    await expect(authApi.me()).resolves.toMatchObject({ email: 'ana@umb.edu.co' })
    expect(calls).toEqual([
      'GET /api/v1/users/me',
      'POST /api/v1/auth/refresh',
      'GET /api/v1/users/me',
    ])
  })

  it('varias solicitudes con 401 simultáneas comparten una sola renovación', async () => {
    useAuthStore.setState({ accessToken: 'viejo', refreshToken: 'refresh-1' })
    const { calls } = mockApi({
      'POST /api/v1/auth/refresh': () => ({ json: { access_token: 'nuevo', expires_in: 900 } }),
      'GET /api/v1/users/me': ({ headers }) =>
        headers.Authorization === 'Bearer nuevo'
          ? { json: ANA }
          : { status: 401, json: { detail: 'x' } },
    })

    await Promise.all([authApi.me(), authApi.me(), authApi.me()])

    expect(calls.filter((c) => c === 'POST /api/v1/auth/refresh')).toHaveLength(1)
  })

  it('no reintenta indefinidamente: si la renovación falla, propaga el 401', async () => {
    useAuthStore.setState({ accessToken: 'viejo', refreshToken: 'refresh-1' })
    mockApi({
      'POST /api/v1/auth/refresh': () => ({ status: 401, json: { detail: 'x' } }),
      'GET /api/v1/users/me': () => ({
        status: 401,
        json: { detail: 'Token inválido o expirado' },
      }),
    })

    await expect(authApi.me()).rejects.toMatchObject({ status: 401 })
    expect(useAuthStore.getState().refreshToken).toBeNull() // sesión cerrada
  })

  it('los endpoints públicos no intentan renovar el token', async () => {
    useAuthStore.setState({ refreshToken: 'refresh-1' })
    const { calls } = mockApi({
      'POST /api/v1/auth/login': () => ({
        status: 401,
        json: { detail: 'Credenciales inválidas' },
      }),
    })

    await expect(authApi.login('a@umb.edu.co', 'x')).rejects.toBeInstanceOf(ApiError)
    expect(calls).toEqual(['POST /api/v1/auth/login'])
  })

  it('una caída de red no cierra la sesión', async () => {
    useAuthStore.setState({ accessToken: 'viejo', refreshToken: 'refresh-1' })
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(authApi.me()).rejects.toMatchObject({ status: 0 })
    expect(useAuthStore.getState().refreshToken).toBe('refresh-1')
  })

  it('convierte errores 422 del servidor en un mensaje genérico legible', async () => {
    mockApi({
      'POST /api/v1/auth/register': () => ({ status: 422, json: { detail: [{ msg: 'x' }] } }),
    })

    await expect(authApi.register({ email: 'a@umb.edu.co', password: 'x' })).rejects.toMatchObject({
      status: 422,
      message: 'Ocurrió un error inesperado. Intenta de nuevo.',
    })
  })
})
