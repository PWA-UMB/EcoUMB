import type { ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useAuthStore } from '@/stores/authStore'

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="size-6"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  )
}

const LINKS = [
  {
    to: '/',
    label: 'Inicio',
    end: true,
    icon: <path d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />,
  },
  {
    to: '/escanear',
    label: 'Escanear',
    end: false,
    icon: (
      <>
        <path d="M4 8a2 2 0 0 1 2-2h1.5l1.2-2h6.6l1.2 2H18a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" />
        <circle cx="12" cy="13" r="3.5" />
      </>
    ),
  },
  {
    to: '/historial',
    label: 'Historial',
    end: false,
    icon: (
      <>
        <path d="M8 6h12M8 12h12M8 18h12" />
        <path d="M4 6h.01M4 12h.01M4 18h.01" />
      </>
    ),
  },
  {
    to: '/aprende',
    label: 'Aprende',
    end: false,
    icon: (
      <>
        <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v15H5.5A1.5 1.5 0 0 0 4 20.5z" />
        <path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v15h5.5a1.5 1.5 0 0 1 1.5 1.5z" />
      </>
    ),
  },
  {
    to: '/perfil',
    label: 'Perfil',
    end: false,
    icon: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21a8 8 0 0 1 16 0" />
      </>
    ),
  },
] as const

/** Marco de las pantallas autenticadas: cabecera y navegación (barra inferior en móvil, pestañas en escritorio). */
export function AppShell() {
  const logout = useAuthStore((s) => s.logout)

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-forest-900/10 bg-forest-50/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3 sm:px-8">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" className="size-9 rounded-xl" />
            <span className="font-display text-xl font-bold tracking-tight">EcoUMB</span>
          </div>

          <Button variant="secondary" onClick={logout}>
            Cerrar sesión
          </Button>
        </div>
      </header>

      {/* Fuera del <header>: su `backdrop-blur` haría que `fixed` se midiera contra la cabecera y no contra la pantalla. */}
      <nav
        aria-label="Principal"
        className="fixed inset-x-0 bottom-0 z-30 border-t border-forest-900/10 bg-white pb-[env(safe-area-inset-bottom)] md:static md:border-0 md:bg-transparent md:pb-0"
      >
        <div className="mx-auto grid max-w-3xl grid-cols-5 md:flex md:gap-1 md:px-8 md:pt-4">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs font-semibold md:min-h-11 md:flex-row md:gap-2 md:rounded-xl md:px-4 md:text-sm ${
                  isActive
                    ? 'text-forest-900 md:bg-forest-100'
                    : 'text-forest-900/60 hover:text-forest-900'
                }`
              }
            >
              <Icon>{link.icon}</Icon>
              {link.label}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="mx-auto max-w-3xl px-4 pb-28 pt-6 sm:px-8 md:pb-10">
        <Outlet />
      </div>
    </div>
  )
}
