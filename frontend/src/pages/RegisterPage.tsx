import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'

import { AuthLayout } from '@/components/AuthLayout'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { authApi } from '@/features/auth/authApi'
import { describeAuthError } from '@/features/auth/errors'
import { registerSchema, type RegisterValues } from '@/features/auth/schemas'
import { ApiError } from '@/lib/api'

export function RegisterPage() {
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { fullName: '', email: '', password: '', confirmPassword: '' },
  })

  const mutation = useMutation({
    mutationFn: (values: RegisterValues) =>
      authApi.register({
        email: values.email,
        password: values.password,
        full_name: values.fullName || undefined,
      }),
    onSuccess: (user) =>
      navigate('/login', { replace: true, state: { registeredEmail: user.email } }),
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        setError('email', { message: describeAuthError(error, 'register') }, { shouldFocus: true })
      }
    },
  })

  const isConflict = mutation.error instanceof ApiError && mutation.error.status === 409

  return (
    <AuthLayout title="Crea tu cuenta" subtitle="Toma menos de un minuto.">
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        noValidate
        className="space-y-4"
      >
        {mutation.isError && !isConflict && (
          <Alert tone="error">{describeAuthError(mutation.error, 'register')}</Alert>
        )}

        <FormField
          label="Nombre (opcional)"
          autoComplete="name"
          error={errors.fullName?.message}
          {...register('fullName')}
        />
        <FormField
          label="Correo electrónico"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder="nombre@umb.edu.co"
          error={errors.email?.message}
          {...register('email')}
        />
        <FormField
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          hint="Mínimo 8 caracteres, con al menos una letra y un número."
          error={errors.password?.message}
          {...register('password')}
        />
        <FormField
          label="Confirmar contraseña"
          type="password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />

        <Button type="submit" block loading={mutation.isPending}>
          {mutation.isPending ? 'Creando cuenta…' : 'Crear cuenta'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-forest-900/80">
        ¿Ya tienes cuenta?{' '}
        <Link to="/login" className="font-semibold text-forest-800 underline underline-offset-2">
          Inicia sesión
        </Link>
      </p>
    </AuthLayout>
  )
}
