import { useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { classificationApi } from '@/features/classification/classificationApi'
import { HistoryRow } from '@/features/classification/HistoryRow'

const PAGE_SIZE = 10

/** RF-16 y RF-17: registro paginado de las clasificaciones del usuario, de la más reciente a la más antigua. */
export function HistoryPage() {
  const history = useInfiniteQuery({
    queryKey: ['history', 'list'],
    queryFn: ({ pageParam }) => classificationApi.history(PAGE_SIZE, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last) =>
      last.offset + last.items.length < last.total ? last.offset + last.limit : undefined,
  })

  const records = history.data?.pages.flatMap((page) => page.items) ?? []
  const total = history.data?.pages[0]?.total ?? 0

  return (
    <main className="space-y-6">
      <h1 className="font-display text-3xl font-bold tracking-tight">Historial</h1>

      {history.isPending && (
        <p role="status" className="text-forest-900/70">
          Cargando tu historial…
        </p>
      )}

      {history.isError && (
        <div className="space-y-3">
          <Alert tone="error">No se pudo cargar tu historial. Intenta de nuevo.</Alert>
          <Button variant="secondary" onClick={() => void history.refetch()}>
            Reintentar
          </Button>
        </div>
      )}

      {history.isSuccess && records.length === 0 && (
        <section className="rounded-2xl border border-dashed border-forest-900/30 p-6">
          <p className="font-semibold">Aún no has clasificado ningún residuo.</p>
          <p className="mt-1 text-forest-900/70">Tus clasificaciones quedarán registradas aquí.</p>
          <Link
            to="/escanear"
            className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-forest-900 px-5 font-semibold text-forest-50 hover:bg-forest-800"
          >
            Escanear un residuo
          </Link>
        </section>
      )}

      {records.length > 0 && (
        <>
          <p className="text-sm text-forest-900/70">
            {total} {total === 1 ? 'clasificación' : 'clasificaciones'}
          </p>
          <ul aria-label="Clasificaciones" className="space-y-3">
            {records.map((record) => (
              <HistoryRow key={record.id} record={record} />
            ))}
          </ul>
          {history.hasNextPage && (
            <Button
              variant="secondary"
              loading={history.isFetchingNextPage}
              onClick={() => void history.fetchNextPage()}
            >
              Cargar más
            </Button>
          )}
        </>
      )}
    </main>
  )
}
