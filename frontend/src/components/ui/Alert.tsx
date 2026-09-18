import type { ReactNode } from 'react'

interface AlertProps {
  tone: 'error' | 'success'
  children: ReactNode
}

const tones = {
  error: 'border-red-300 bg-red-50 text-red-900',
  success: 'border-forest-300 bg-forest-100 text-forest-900',
} as const

/** `role="alert"` anuncia el mensaje a lectores de pantalla en cuanto aparece. */
export function Alert({ tone, children }: AlertProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`rounded-xl border px-4 py-3 text-sm font-medium ${tones[tone]}`}
    >
      {children}
    </div>
  )
}
