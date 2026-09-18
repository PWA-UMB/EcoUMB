import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { authApi, type User } from '@/features/auth/authApi'
import { ApiError, configureAuth } from '@/lib/api'

/**
 * Sesión (RF-02). Decisión de almacenamiento (ADR-005):
 *  - access token: solo en memoria (vive 15 min, no sobrevive a un XSS persistente);
 *  - refresh token: `localStorage`, para que la sesión persista al recargar (criterio S1-08).
 */
export type SessionStatus = 'checking' | 'authenticated' | 'anonymous'

interface AuthState {
  status: SessionStatus
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Recupera la sesión al abrir la app a partir del refresh token guardado. */
  bootstrap: () => Promise<void>
  refreshAccessToken: () => Promise<string | null>
}

let inflightRefresh: Promise<string | null> | null = null

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      status: 'checking',
      user: null,
      accessToken: null,
      refreshToken: null,

      login: async (email, password) => {
        const tokens = await authApi.login(email, password)
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token })
        try {
          const user = await authApi.me()
          set({ user, status: 'authenticated' })
        } catch (error) {
          get().logout()
          throw error
        }
      },

      logout: () => set({ accessToken: null, refreshToken: null, user: null, status: 'anonymous' }),

      bootstrap: async () => {
        const token = get().refreshToken ? await get().refreshAccessToken() : null
        if (!token) {
          set({ status: 'anonymous' })
          return
        }
        try {
          set({ user: await authApi.me(), status: 'authenticated' })
        } catch {
          set({ status: 'anonymous' })
        }
      },

      // Una sola renovación a la vez, aunque varias solicitudes reciban 401 al mismo tiempo.
      refreshAccessToken: () => {
        const refreshToken = get().refreshToken
        if (!refreshToken) return Promise.resolve(null)
        inflightRefresh ??= authApi
          .refresh(refreshToken)
          .then((result) => {
            set({ accessToken: result.access_token })
            return result.access_token
          })
          .catch((error: unknown) => {
            // Refresh inválido o vencido: la sesión terminó. Un fallo de red no cierra sesión.
            if (error instanceof ApiError && error.status === 401) get().logout()
            return null
          })
          .finally(() => {
            inflightRefresh = null
          })
        return inflightRefresh
      },
    }),
    {
      name: 'ecoumb.session',
      partialize: (state) => ({ refreshToken: state.refreshToken }),
    },
  ),
)

configureAuth({
  getAccessToken: () => useAuthStore.getState().accessToken,
  refreshAccessToken: () => useAuthStore.getState().refreshAccessToken(),
})
