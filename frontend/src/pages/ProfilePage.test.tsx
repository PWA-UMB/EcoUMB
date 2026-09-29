import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ANA, EMPTY_HISTORY, mockApi, renderApp, SESSION_ROUTES, startSession } from '@/test/utils'

const HOME_ROUTES = {
  ...SESSION_ROUTES,
  'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
}

describe('Perfil (RF-04)', () => {
  beforeEach(() => startSession())

  it('muestra correo, rol, puntos y nivel de la cuenta', async () => {
    mockApi(HOME_ROUTES)
    renderApp('/perfil')

    expect(await screen.findByRole('heading', { name: 'Mi perfil' })).toBeInTheDocument()
    expect(screen.getByText('ana@umb.edu.co')).toBeInTheDocument()
    expect(screen.getByText('Usuario')).toBeInTheDocument()
    expect(screen.getByLabelText('Nombre')).toHaveValue('Ana Pérez')
  })

  it.each([
    ['cleaner', 'Personal de aseo'],
    ['admin', 'Administrador'],
  ])('traduce el rol %s a «%s»', async (role, label) => {
    mockApi({ ...HOME_ROUTES, 'GET /api/v1/users/me': () => ({ json: { ...ANA, role } }) })
    renderApp('/perfil')

    expect(await screen.findByText(label)).toBeInTheDocument()
  })

  it('guarda el nuevo nombre y lo refleja en la sesión', async () => {
    const { fetchMock } = mockApi({
      ...HOME_ROUTES,
      'PATCH /api/v1/users/me': ({ body }) => ({
        json: { ...ANA, full_name: (body as { full_name: string }).full_name },
      }),
    })
    renderApp('/perfil')
    const field = await screen.findByLabelText('Nombre')

    await userEvent.clear(field)
    await userEvent.type(field, '  Ana María  ')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText('Perfil actualizado.')).toBeInTheDocument()
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(patch![1]!.body))).toEqual({ full_name: 'Ana María' })
  })

  it('un nombre vacío se envía como null', async () => {
    const { fetchMock } = mockApi({
      ...HOME_ROUTES,
      'PATCH /api/v1/users/me': () => ({ json: { ...ANA, full_name: null } }),
    })
    renderApp('/perfil')

    await userEvent.clear(await screen.findByLabelText('Nombre'))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await screen.findByText('Perfil actualizado.')
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(patch![1]!.body))).toEqual({ full_name: null })
  })

  it('valida el largo máximo antes de llamar al servidor', async () => {
    const { calls } = mockApi(HOME_ROUTES)
    renderApp('/perfil')
    const field = await screen.findByLabelText('Nombre')

    await userEvent.clear(field)
    await userEvent.type(field, 'a'.repeat(121))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText('Máximo 120 caracteres')).toBeInTheDocument()
    expect(calls).not.toContain('PATCH /api/v1/users/me')
  })

  it('si el servidor falla, lo informa sin perder lo escrito', async () => {
    mockApi({
      ...HOME_ROUTES,
      'PATCH /api/v1/users/me': () => ({ status: 500, json: { detail: 'x' } }),
    })
    renderApp('/perfil')
    const field = await screen.findByLabelText('Nombre')

    await userEvent.clear(field)
    await userEvent.type(field, 'Otro nombre')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar')
    expect(field).toHaveValue('Otro nombre')
  })
})
