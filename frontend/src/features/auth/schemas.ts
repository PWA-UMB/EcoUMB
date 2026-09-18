import { z } from 'zod'

/** Reglas idénticas a las del backend (`RegisterRequest`): validar antes de enviar (RNF-09/11). */
const BCRYPT_MAX_BYTES = 72

const password = z
  .string()
  .min(8, 'Usa al menos 8 caracteres')
  .refine((v) => new TextEncoder().encode(v).length <= BCRYPT_MAX_BYTES, {
    message: 'La contraseña es demasiado larga (máximo 72 bytes)',
  })
  .refine((v) => /\p{L}/u.test(v) && /\p{Nd}/u.test(v), {
    message: 'Incluye al menos una letra y un número',
  })

const email = z
  .string()
  .trim()
  .min(1, 'Ingresa tu correo')
  .pipe(z.email('Ingresa un correo válido'))

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Ingresa tu contraseña'),
})

export const registerSchema = z
  .object({
    fullName: z.string().trim().max(120, 'Máximo 120 caracteres').optional(),
    email,
    password,
    confirmPassword: z.string().min(1, 'Confirma tu contraseña'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Las contraseñas no coinciden',
  })

export type LoginValues = z.infer<typeof loginSchema>
export type RegisterValues = z.infer<typeof registerSchema>
