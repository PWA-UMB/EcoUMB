import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { ROLE_LABEL } from '@/features/auth/roles'
import { profileSchema, type ProfileValues } from '@/features/auth/schemas'
import { useAuthStore } from '@/stores/authStore'

/** RF-04: datos de la cuenta y edición del nombre visible. */
export function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const updateProfile = useAuthStore((s) => s.updateProfile)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { fullName: user?.full_name ?? '' },
  })

  const mutation = useMutation({
    mutationFn: (values: ProfileValues) => updateProfile(values.fullName || null),
  })

  if (!user) return null

  return (
    <main className="space-y-8">
      <h1 className="font-display text-3xl font-bold tracking-tight">Mi perfil</h1>

      <dl className="grid gap-4 rounded-2xl bg-white p-5 shadow-card sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-forest-900/70">Correo institucional</dt>
          <dd className="mt-1 break-all font-semibold">{user.email}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-forest-900/70">Rol</dt>
          <dd className="mt-1 font-semibold">{ROLE_LABEL[user.role]}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-forest-900/70">Puntos</dt>
          <dd className="mt-1 font-semibold">{user.total_points}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-forest-900/70">Nivel</dt>
          <dd className="mt-1 font-semibold">{user.level}</dd>
        </div>
      </dl>

      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        noValidate
        className="space-y-4"
        aria-label="Editar perfil"
      >
        {mutation.isSuccess && <Alert tone="success">Perfil actualizado.</Alert>}
        {mutation.isError && (
          <Alert tone="error">No se pudo guardar el cambio. Intenta de nuevo.</Alert>
        )}
        <FormField
          label="Nombre"
          autoComplete="name"
          hint="Es opcional. Si lo dejas vacío, se muestra tu correo."
          error={errors.fullName?.message}
          {...register('fullName')}
        />
        <Button type="submit" loading={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar cambios'}
        </Button>
      </form>
    </main>
  )
}
