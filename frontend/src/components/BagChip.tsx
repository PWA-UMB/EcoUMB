import { BAGS } from '@/features/classification/labels'

/** Etiqueta con el color de la bolsa donde va el residuo (blanca, negra o verde). */
export function BagChip({ color }: { color: string }) {
  const bag = BAGS[color] ?? { label: `Bolsa ${color}`, className: 'bg-forest-100 text-forest-950' }
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-sm font-semibold ${bag.className}`}
    >
      {bag.label}
    </span>
  )
}
