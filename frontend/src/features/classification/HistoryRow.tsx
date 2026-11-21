import { AuthedImage } from '@/components/AuthedImage'
import { BagChip } from '@/components/BagChip'
import { formatDateTime, formatPercent } from '@/lib/format'

import type { ClassificationResult } from './classificationApi'
import { BAND_LABEL } from './labels'

/** Una fila del historial: miniatura, objeto, bolsa, fecha y confianza (RF-16, RF-17). */
export function HistoryRow({ record }: { record: ClassificationResult }) {
  return (
    <li className="flex items-center gap-4 rounded-2xl bg-white p-3 shadow-card">
      <AuthedImage
        path={record.image_url}
        alt={`Foto de ${record.item.display_name}`}
        className="size-16 shrink-0 rounded-xl object-cover"
      />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="truncate font-semibold">{record.item.display_name}</p>
        <div className="flex flex-wrap items-center gap-2">
          <BagChip color={record.category.bag_color} />
          <span className="text-sm text-forest-900/70">
            {BAND_LABEL[record.confidence_band]} · {formatPercent(record.confidence)}
          </span>
        </div>
        <p className="text-xs text-forest-900/60">
          <time dateTime={record.created_at}>{formatDateTime(record.created_at)}</time>
          {record.simulated && ' · simulado'}
        </p>
        {record.feedback && (
          <p className="text-xs font-medium text-forest-800">
            {record.feedback.was_corrected
              ? `Corregido: era ${record.feedback.item.display_name}`
              : 'Confirmado por ti'}
          </p>
        )}
      </div>
    </li>
  )
}
