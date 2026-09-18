import { Button } from '@/components/ui/Button'
import { useAuthStore } from '@/stores/authStore'

/** Pantalla Home provisional del Sprint 1: confirma que la sesión funciona (S1-08). */
export function HomePage() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  if (!user) return null

  const name = user.full_name ?? user.email

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col px-4 py-6 sm:px-8">
      <header className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-9 rounded-xl" />
          <span className="font-display text-xl font-bold tracking-tight">EcoUMB</span>
        </div>
        <Button variant="secondary" onClick={logout}>
          Cerrar sesión
        </Button>
      </header>

      <main className="mt-10 flex-1 space-y-8">
        <div>
          <p className="text-forest-900/70">Hola,</p>
          <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">{name}</h1>
        </div>

        <dl className="grid grid-cols-2 gap-4">
          <div className="rounded-2xl bg-white p-5 shadow-card">
            <dt className="text-sm font-medium text-forest-900/70">Puntos</dt>
            <dd className="mt-1 font-display text-4xl font-bold">{user.total_points}</dd>
          </div>
          <div className="rounded-2xl bg-forest-900 p-5 text-forest-50 shadow-card">
            <dt className="text-sm font-medium text-forest-300">Nivel</dt>
            <dd className="mt-1 font-display text-4xl font-bold">{user.level}</dd>
          </div>
        </dl>

        <section
          aria-labelledby="scan-title"
          className="rounded-2xl border border-dashed border-forest-900/30 p-6"
        >
          <h2 id="scan-title" className="font-display text-xl font-bold">
            Escanear un residuo
          </h2>
          <p className="mt-1 text-forest-900/70">
            La captura con cámara y la clasificación llegan en el Sprint 2.
          </p>
          <Button className="mt-4" disabled>
            Próximamente
          </Button>
        </section>
      </main>
    </div>
  )
}
