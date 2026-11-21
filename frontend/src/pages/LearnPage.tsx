import { useQuery } from '@tanstack/react-query'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { BagChip } from '@/components/BagChip'
import { CATEGORY_LABEL } from '@/features/classification/labels'
import { educationApi } from '@/features/education/educationApi'

/** RF-26, RF-27, RF-28: qué va en cada bolsa según la norma, con los objetos del catálogo y buenas prácticas. */
export function LearnPage() {
  const education = useQuery({
    queryKey: ['education'],
    queryFn: educationApi.get,
    staleTime: 3_600_000,
  })

  return (
    <main className="space-y-8">
      <h1 className="font-display text-3xl font-bold tracking-tight">Aprende a separar</h1>

      {education.isPending && (
        <p role="status" className="text-forest-900/70">
          Cargando la guía…
        </p>
      )}

      {education.isError && (
        <div className="space-y-3">
          <Alert tone="error">No se pudo cargar la guía. Intenta de nuevo.</Alert>
          <Button variant="secondary" onClick={() => void education.refetch()}>
            Reintentar
          </Button>
        </div>
      )}

      {education.isSuccess && (
        <>
          <section
            aria-labelledby="normative-title"
            className="rounded-3xl bg-forest-900 p-6 text-forest-50"
          >
            <h2 id="normative-title" className="font-display text-xl font-bold">
              {education.data.normative.title}
            </h2>
            <p className="mt-2 text-forest-100">{education.data.normative.summary}</p>
            <p className="mt-3 text-sm text-forest-300">{education.data.normative.note}</p>
          </section>

          {education.data.bags.map((bag) => (
            <section
              key={bag.category}
              aria-labelledby={`bag-${bag.category}`}
              className="space-y-3 rounded-3xl bg-white p-5 shadow-card"
            >
              <div className="flex flex-wrap items-center gap-3">
                <BagChip color={bag.bag_color} />
                <h2 id={`bag-${bag.category}`} className="font-display text-xl font-bold">
                  {CATEGORY_LABEL[bag.category] ?? bag.category}
                </h2>
              </div>
              <p className="font-medium">{bag.description}</p>
              <p className="text-forest-900/80">{bag.educational_text}</p>
              <ul
                aria-label={`Objetos de la bolsa ${bag.bag_color}`}
                className="divide-y divide-forest-900/10"
              >
                {bag.items.map((item) => (
                  <li key={item.code} className="py-2.5">
                    <p className="font-semibold">{item.display_name}</p>
                    <p className="text-sm text-forest-900/70">{item.disposal_tip}</p>
                  </li>
                ))}
              </ul>
            </section>
          ))}

          <section aria-labelledby="practices-title" className="space-y-3">
            <h2 id="practices-title" className="font-display text-xl font-bold">
              Buenas prácticas
            </h2>
            <ul className="grid gap-3 sm:grid-cols-2">
              {education.data.practices.map((practice) => (
                <li key={practice.title} className="rounded-2xl bg-forest-100 p-4">
                  <p className="font-semibold">{practice.title}</p>
                  <p className="mt-1 text-sm text-forest-900/80">{practice.text}</p>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  )
}
