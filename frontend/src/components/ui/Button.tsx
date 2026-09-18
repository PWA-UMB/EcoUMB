import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'

const button = cva(
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 text-base font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60',
  {
    variants: {
      variant: {
        primary: 'bg-forest-900 text-forest-50 hover:bg-forest-800 active:bg-forest-950',
        secondary: 'border border-forest-900/20 bg-white text-forest-900 hover:bg-forest-100',
        ghost: 'text-forest-800 hover:bg-forest-100',
      },
      block: { true: 'w-full', false: '' },
    },
    defaultVariants: { variant: 'primary', block: false },
  },
)

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof button> {
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, block, loading = false, disabled, children, className, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={[button({ variant, block }), className].filter(Boolean).join(' ')}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  )
})
