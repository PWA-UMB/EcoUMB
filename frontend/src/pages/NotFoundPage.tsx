import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="font-display text-4xl font-bold">Página no encontrada</h1>
      <p className="text-forest-900/70">La dirección que buscas no existe o fue movida.</p>
      <Link to="/" className="font-semibold text-forest-800 underline underline-offset-2">
        Volver al inicio
      </Link>
    </main>
  )
}
