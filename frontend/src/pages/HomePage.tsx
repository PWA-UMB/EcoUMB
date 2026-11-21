import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { classificationApi } from '@/features/classification/classificationApi'
import { HistoryRow } from '@/features/classification/HistoryRow'
import { useInstallPrompt } from '@/hooks/useInstallPrompt'
import { useAuthStore } from '@/stores/authStore'

const RECENT_COUNT = 3

/** Inicio: saludo, puntos, acceso directo a escanear y las últimas clasificaciones. */
export function HomePage() {
  const user = useAuthStore((s) => s.user)
  const { canInstall, install } = useInstallPrompt()
  const recent = useQuery({
    queryKey: ['history', 'recent'],
    queryFn: () => classificationApi.history(RECENT_COUNT, 0),
  })
  if (!user) return null

  const name = user.full_name ?? user.email
  const records = recent.data?.items ?? []

  return (
    <main className="space-y-8">
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

      <section aria-labelledby="scan-title" className="rounded-3xl bg-forest-100 p-6">
        <h2 id="scan-title" className="font-display text-xl font-bold">
          ¿Qué hago con este residuo?
        </h2>
        <p className="mt-1 text-forest-900/80">Tómale una foto y te decimos en qué bolsa va.</p>
        <Link
          to="/escanear"
          className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-forest-900 px-5 font-semibold text-forest-50 hover:bg-forest-800"
        >
          Escanear un residuo
        </Link>
      </section>

      <section aria-labelledby="recent-title" className="space-y-3">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="recent-title" className="font-display text-xl font-bold">
            Últimas clasificaciones
          </h2>
          {records.length > 0 && (
            <Link to="/historial" className="text-sm font-semibold text-forest-800 underline">
              Ver todo
            </Link>
          )}
        </div>
        {recent.isSuccess && records.length === 0 && (
          <p className="text-forest-900/70">Aún no has clasificado ningún residuo.</p>
        )}
        {records.length > 0 && (
          <ul aria-label="Últimas clasificaciones" className="space-y-3">
            {records.map((record) => (
              <HistoryRow key={record.id} record={record} />
            ))}
          </ul>
        )}
      </section>

      {canInstall && (
        <Button variant="secondary" onClick={() => void install()}>
          Instalar la aplicación
        </Button>
      )}
    </main>
  )
}
