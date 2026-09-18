import type { ReactNode } from 'react'

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: ReactNode
}

/** Las tres bolsas de la Resolución 2184 son el motivo de marca: blanca, negra y verde. */
function BagDots() {
  return (
    <div className="flex items-center gap-2" aria-hidden="true">
      <span className="size-4 rounded-full border border-forest-900/30 bg-bag-white" />
      <span className="size-4 rounded-full bg-bag-black" />
      <span className="size-4 rounded-full bg-bag-green" />
    </div>
  )
}

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-dvh flex-col lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <header className="bg-forest-900 px-4 pb-16 pt-8 text-forest-50 sm:px-8 lg:flex lg:flex-col lg:justify-between lg:px-14 lg:py-14">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-10 rounded-xl" />
          <span className="font-display text-2xl font-bold tracking-tight">EcoUMB</span>
        </div>
        <div className="mt-8 max-w-md space-y-4 lg:mt-0">
          <BagDots />
          <p className="font-display text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
            Cada residuo en su bolsa, cada acierto suma.
          </p>
          <p className="text-forest-100/80">
            Clasifica según el código de colores de la Resolución 2184 de 2019 y ayuda a que la
            Universidad Manuela Beltrán gestione mejor sus residuos.
          </p>
        </div>
        <p className="hidden text-sm text-forest-300 lg:block">
          Universidad Manuela Beltrán · Sede Bogotá
        </p>
      </header>

      <main className="-mt-10 flex flex-1 items-start justify-center px-4 pb-10 sm:px-8 lg:mt-0 lg:items-center">
        <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-card sm:p-8">
          <h1 className="font-display text-2xl font-bold tracking-tight text-forest-950">
            {title}
          </h1>
          <p className="mb-6 mt-1 text-forest-900/70">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  )
}
