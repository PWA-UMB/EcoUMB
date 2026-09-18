import { loginSchema, registerSchema } from './schemas'

const valid = {
  fullName: 'Ana Pérez',
  email: 'ana@umb.edu.co',
  password: 'Clave-Segura-2026',
  confirmPassword: 'Clave-Segura-2026',
}

function firstMessage(input: unknown) {
  const result = registerSchema.safeParse(input)
  return result.success ? null : result.error.issues[0]?.message
}

describe('registerSchema', () => {
  it('acepta datos válidos', () => {
    expect(registerSchema.safeParse(valid).success).toBe(true)
  })

  it('exige al menos 8 caracteres', () => {
    expect(firstMessage({ ...valid, password: 'a1', confirmPassword: 'a1' })).toMatch(
      /8 caracteres/,
    )
  })

  it.each(['sololetrasaqui', '1234567890'])('exige letra y número: %s', (password) => {
    expect(firstMessage({ ...valid, password, confirmPassword: password })).toMatch(
      /letra y un número/,
    )
  })

  it('rechaza contraseñas de más de 72 bytes (límite de bcrypt)', () => {
    const long = 'á'.repeat(40) + '1' // 41 caracteres, 81 bytes
    expect(firstMessage({ ...valid, password: long, confirmPassword: long })).toMatch(/72 bytes/)
  })

  it('exige que las contraseñas coincidan', () => {
    expect(firstMessage({ ...valid, confirmPassword: 'Otra-Clave-1' })).toBe(
      'Las contraseñas no coinciden',
    )
  })

  it('rechaza correos mal formados', () => {
    expect(firstMessage({ ...valid, email: 'no-es-correo' })).toBe('Ingresa un correo válido')
  })
})

describe('loginSchema', () => {
  it('no impone reglas de fortaleza al iniciar sesión, solo que no esté vacío', () => {
    expect(loginSchema.safeParse({ email: 'ana@umb.edu.co', password: 'x' }).success).toBe(true)
    expect(loginSchema.safeParse({ email: 'ana@umb.edu.co', password: '' }).success).toBe(false)
  })
})
