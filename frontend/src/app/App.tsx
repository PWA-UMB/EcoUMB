import { useEffect } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'

import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { useAuthStore } from '@/stores/authStore'

function CheckingSession() {
  return (
    <div role="status" className="grid min-h-dvh place-items-center text-forest-900/70">
      Cargando…
    </div>
  )
}

/** Rutas que exigen sesión; el destino original se conserva para volver tras el login. */
function RequireAuth() {
  const status = useAuthStore((s) => s.status)
  const location = useLocation()
  if (status === 'checking') return <CheckingSession />
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

/** Login y registro no tienen sentido con una sesión activa. */
function PublicOnly() {
  const status = useAuthStore((s) => s.status)
  if (status === 'checking') return <CheckingSession />
  if (status === 'authenticated') return <Navigate to="/" replace />
  return <Outlet />
}

export function App() {
  const bootstrap = useAuthStore((s) => s.bootstrap)
  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/registro" element={<RegisterPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/" element={<HomePage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
