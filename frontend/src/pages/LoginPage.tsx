import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { AuthLayout } from '@/components/AuthLayout'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { describeAuthError } from '@/features/auth/errors'
import { loginSchema, type LoginValues } from '@/features/auth/schemas'
import { useAuthStore } from '@/stores/authStore'

interface LocationState {
  from?: { pathname: string }
  registeredEmail?: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const state = (useLocation().state ?? {}) as LocationState
  const login = useAuthStore((s) => s.login)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: state.registeredEmail ?? '', password: '' },
  })

  const mutation = useMutation({
    mutationFn: (values: LoginValues) => login(values.email, values.password),
    onSuccess: () => navigate(state.from?.pathname ?? '/', { replace: true }),
  })

  return (
    <AuthLayout title="Inicia sesión" subtitle="Ingresa con tu correo para continuar.">
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        noValidate
        className="space-y-4"
      >
        {state.registeredEmail && !mutation.isError && (
          <Alert tone="success">Cuenta creada. Ahora inicia sesión para continuar.</Alert>
        )}
        {mutation.isError && (
          <Alert tone="error">{describeAuthError(mutation.error, 'login')}</Alert>
        )}

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
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />

        <Button type="submit" block loading={mutation.isPending}>
          {mutation.isPending ? 'Ingresando…' : 'Iniciar sesión'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-forest-900/80">
        ¿Aún no tienes cuenta?{' '}
        <Link to="/registro" className="font-semibold text-forest-800 underline underline-offset-2">
          Regístrate
        </Link>
      </p>
    </AuthLayout>
  )
}
