import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ANA, mockApi, renderApp, type MockCall } from '@/test/utils'

async function fillForm({
  name = '',
  email = 'ana@umb.edu.co',
  password = 'Clave-Segura-2026',
  confirm = 'Clave-Segura-2026',
} = {}) {
  const user = userEvent.setup()
  if (name) await user.type(screen.getByLabelText('Nombre (opcional)'), name)
  await user.type(screen.getByLabelText('Correo electrónico'), email)
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.type(screen.getByLabelText('Confirmar contraseña'), confirm)
  await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))
}

describe('Registro (S1-08)', () => {
  it('valida contraseña débil y confirmación distinta sin llamar al servidor', async () => {
    const { fetchMock } = mockApi({})
    renderApp('/registro')
    await screen.findByRole('button', { name: 'Crear cuenta' })

    await fillForm({ password: 'corta', confirm: 'otra' })

    expect(await screen.findByText('Usa al menos 8 caracteres')).toBeInTheDocument()
    expect(screen.getByText('Las contraseñas no coinciden')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('crea la cuenta y lleva al login con aviso y correo precargado', async () => {
    let received: MockCall | undefined
    mockApi({
      'POST /api/v1/auth/register': (call) => {
        received = call
        return { status: 201, json: ANA }
      },
    })
    renderApp('/registro')
    await screen.findByRole('button', { name: 'Crear cuenta' })

    await fillForm({ name: 'Ana Pérez' })

    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument()
    expect(screen.getByText(/Cuenta creada/)).toBeInTheDocument()
    expect(screen.getByLabelText('Correo electrónico')).toHaveValue('ana@umb.edu.co')
    // No se envía la confirmación de contraseña ni ningún rol.
    expect(received?.body).toEqual({
      email: 'ana@umb.edu.co',
      password: 'Clave-Segura-2026',
      full_name: 'Ana Pérez',
    })
  })

  it('no envía full_name cuando el nombre queda vacío', async () => {
    let received: MockCall | undefined
    mockApi({
      'POST /api/v1/auth/register': (call) => {
        received = call
        return { status: 201, json: ANA }
      },
    })
    renderApp('/registro')
    await screen.findByRole('button', { name: 'Crear cuenta' })

    await fillForm()
    await screen.findByRole('heading', { name: 'Inicia sesión' })

    expect(received?.body).not.toHaveProperty('full_name')
  })

  it('un correo repetido (409) se marca en el campo de correo', async () => {
    mockApi({
      'POST /api/v1/auth/register': () => ({
        status: 409,
        json: { detail: 'El correo ya está registrado' },
      }),
    })
    renderApp('/registro')
    await screen.findByRole('button', { name: 'Crear cuenta' })

    await fillForm()

    const email = await screen.findByLabelText('Correo electrónico')
    expect(email).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText(/Ya existe una cuenta con este correo/)).toBeInTheDocument()
  })
})
