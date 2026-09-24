import { BagChip } from '@/components/BagChip'
import { formatPercent } from '@/lib/format'

import type { ClassificationResult } from './classificationApi'
import { BAND_LABEL, CATEGORY_LABEL } from './labels'

interface ResultCardProps {
  result: ClassificationResult
  /** Foto local para mostrar junto al resultado. */
  imageUrl?: string
}

/** Alcance del modelo v1 (entrenado con TrashNet): se declara en pantalla para no sobrevender el resultado. */
const MODEL_SCOPE_NOTE =
  'El modelo reconoce materiales comunes y aún no cubre todos los objetos del catálogo. Si se equivoca, corrígelo: así aprende.'

/** Resultado de una clasificación: objeto, bolsa, explicación educativa y nivel de confianza (RF-13 a RF-15). */
export function ResultCard({ result, imageUrl }: ResultCardProps) {
  const isLow = result.confidence_band === 'low'
  const others = result.top3.filter((c) => c.code !== result.item.code)

  return (
    <article
      aria-labelledby="result-title"
      className="space-y-5 rounded-3xl bg-white p-5 shadow-card"
    >
      {result.simulated && (
        <p className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900">
          Resultado simulado: no se analizó la foto con un modelo de inteligencia artificial.
        </p>
      )}
      {imageUrl && (
        <img
          src={imageUrl}
          alt="Foto del residuo"
          className="aspect-video w-full rounded-2xl object-cover"
        />
      )}

      {isLow ? (
        <div>
          <h2 id="result-title" className="font-display text-2xl font-bold tracking-tight">
            No logramos identificar este residuo con seguridad
          </h2>
          <p className="mt-1 text-forest-900/70">Estas son las opciones más probables:</p>
        </div>
      ) : (
        <div className="space-y-3">
          <h2 id="result-title" className="font-display text-3xl font-bold tracking-tight">
            {result.item.display_name}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <BagChip color={result.category.bag_color} />
            <span className="rounded-full bg-forest-100 px-3 py-1 text-sm font-medium text-forest-900">
              {CATEGORY_LABEL[result.category.code] ?? result.category.code}
            </span>
          </div>
          <p className="text-lg">{result.message}</p>
          <p className="rounded-xl bg-forest-50 px-4 py-3 text-forest-900">
            <span className="font-semibold">Consejo: </span>
            {result.tip}
          </p>
        </div>
      )}

      <p className="text-sm text-forest-900/70">
        {BAND_LABEL[result.confidence_band]} · {formatPercent(result.confidence)}
        {result.model_version && ` · Modelo ${result.model_version}`}
      </p>
      {result.model_version && <p className="text-xs text-forest-900/60">{MODEL_SCOPE_NOTE}</p>}

      {(isLow || result.confidence_band === 'medium') && others.length > 0 && (
        <section aria-label="Otras posibilidades">
          <h3 className="mb-2 font-semibold">{isLow ? 'Opciones' : 'Otras posibilidades'}</h3>
          <ul className="space-y-2">
            {(isLow ? result.top3 : others).map((candidate) => (
              <li
                key={candidate.code}
                className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-xl border border-forest-900/15 px-3 py-2"
              >
                <span>{candidate.display_name}</span>
                <span className="flex items-center gap-2">
                  <BagChip color={candidate.bag_color} />
                  <span className="whitespace-nowrap text-sm text-forest-900/70">
                    {formatPercent(candidate.confidence)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
