import { request } from '@/lib/api'

export type Role = 'user' | 'cleaner' | 'admin'

export interface User {
  id: string
  email: string
  full_name: string | null
  role: Role
  total_points: number
  level: number
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RegisterPayload {
  email: string
  password: string
  full_name?: string
}

export const authApi = {
  register: (payload: RegisterPayload) =>
    request<User>('/api/v1/auth/register', { method: 'POST', body: payload, auth: false }),

  login: (email: string, password: string) =>
    request<TokenPair>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    }),

  refresh: (refreshToken: string) =>
    request<{ access_token: string; expires_in: number }>('/api/v1/auth/refresh', {
      method: 'POST',
      body: { refresh_token: refreshToken },
      auth: false,
    }),

  me: () => request<User>('/api/v1/users/me'),
}
