export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)} %`
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(iso),
  )
}
