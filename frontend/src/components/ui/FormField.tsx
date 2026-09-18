import { forwardRef, useId, type InputHTMLAttributes } from 'react'

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: string
}

/** Etiqueta + campo + ayuda/error enlazados por ARIA (RNF-09, RNF-11). */
export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(function FormField(
  { label, error, hint, id, className, ...rest },
  ref,
) {
  const generated = useId()
  const fieldId = id ?? generated
  const hintId = `${fieldId}-hint`
  const errorId = `${fieldId}-error`
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ')

  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className="block text-sm font-medium text-forest-900">
        {label}
      </label>
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className={[
          'block min-h-11 w-full rounded-xl border bg-white px-3.5 text-base text-forest-950 placeholder:text-forest-900/40',
          error ? 'border-red-600' : 'border-forest-900/25 hover:border-forest-900/50',
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        {...rest}
      />
      {hint && !error && (
        <p id={hintId} className="text-sm text-forest-900/70">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-sm font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  )
})
