import type { ConfidenceBand } from './classificationApi'

/** Bolsas de la Resolución 2184 de 2019. */
export const BAGS: Record<string, { label: string; className: string }> = {
  blanca: {
    label: 'Bolsa blanca',
    className: 'border border-forest-900/40 bg-white text-forest-950',
  },
  negra: { label: 'Bolsa negra', className: 'bg-bag-black text-white' },
  verde: { label: 'Bolsa verde', className: 'bg-bag-green text-forest-950' },
}

export const CATEGORY_LABEL: Record<string, string> = {
  aprovechable: 'Aprovechable',
  no_aprovechable: 'No aprovechable',
  organico: 'Orgánico',
}

export const BAND_LABEL: Record<ConfidenceBand, string> = {
  high: 'Confianza alta',
  medium: 'Confianza media',
  low: 'Confianza baja',
}
