import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { BagChip } from '@/components/BagChip'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { educationApi } from '@/features/education/educationApi'

import { classificationApi, type ClassificationResult } from './classificationApi'

/**
 * RF-29 y RF-30: el usuario confirma o corrige el resultado. Sus respuestas son las fotos reales
 * etiquetadas que necesita el modelo para mejorar (SAD §7.6), por eso se le avisa del uso.
 */
export function FeedbackPanel({ result }: { result: ClassificationResult }) {
  const queryClient = useQueryClient()
  const [choosing, setChoosing] = useState(false)
  const [saved, setSaved] = useState(result.feedback)

  const send = useMutation({
    mutationFn: (itemCode: string) => classificationApi.sendFeedback(result.id, itemCode),
    onSuccess: (updated) => {
      setSaved(updated.feedback)
      setChoosing(false)
      void queryClient.invalidateQueries({ queryKey: ['history'] })
    },
  })

  if (saved && !choosing) {
    return (
      <section aria-label="Tu respuesta" className="space-y-3 rounded-2xl bg-forest-50 p-4">
        <p role="status" className="font-medium">
          {saved.was_corrected
            ? `Gracias. Guardamos que era: ${saved.item.display_name}.`
            : 'Gracias por confirmar el resultado.'}
        </p>
        <Button variant="ghost" onClick={() => setChoosing(true)}>
          Cambiar mi respuesta
        </Button>
      </section>
    )
  }

  return (
    <section aria-label="¿Es correcto?" className="space-y-3 rounded-2xl bg-forest-50 p-4">
      <h3 className="font-semibold">¿Es correcto el resultado?</h3>
      {send.isError && (
        <Alert tone="error">No se pudo guardar tu respuesta. Intenta de nuevo.</Alert>
      )}
      {choosing ? (
        <ItemPicker
          onPick={(code) => send.mutate(code)}
          onCancel={() => setChoosing(false)}
          disabled={send.isPending}
        />
      ) : (
        <div className="flex flex-wrap gap-3">
          <Button loading={send.isPending} onClick={() => send.mutate(result.item.code)}>
            Sí, es correcto
          </Button>
          <Button variant="secondary" onClick={() => setChoosing(true)}>
            No, corregir
          </Button>
        </div>
      )}
      <p className="text-xs text-forest-900/70">
        Tu respuesta y la foto pueden usarse para mejorar el modelo.
      </p>
    </section>
  )
}

interface ItemPickerProps {
  onPick: (itemCode: string) => void
  onCancel: () => void
  disabled: boolean
}

/** Lista de los objetos del catálogo, agrupados por bolsa, para indicar qué era realmente. */
function ItemPicker({ onPick, onCancel, disabled }: ItemPickerProps) {
  const education = useQuery({
    queryKey: ['education'],
    queryFn: educationApi.get,
    staleTime: 3_600_000,
  })

  if (education.isPending) return <p role="status">Cargando objetos…</p>
  if (education.isError) {
    return <Alert tone="error">No se pudo cargar la lista de objetos. Intenta de nuevo.</Alert>
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-forest-900/80">¿Qué era realmente?</p>
      {education.data.bags.map((bag) => (
        <div key={bag.category} className="space-y-2">
          <BagChip color={bag.bag_color} />
          <ul aria-label={`Objetos de la bolsa ${bag.bag_color}`} className="flex flex-wrap gap-2">
            {bag.items.map((item) => (
              <li key={item.code}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onPick(item.code)}
                  className="min-h-11 rounded-xl border border-forest-900/20 bg-white px-3 text-sm font-medium hover:bg-forest-100 disabled:opacity-60"
                >
                  {item.display_name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <Button variant="ghost" onClick={onCancel}>
        Cancelar
      </Button>
    </div>
  )
}
