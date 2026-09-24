import type { Role } from './authApi'

export const ROLE_LABEL: Record<Role, string> = {
  user: 'Usuario',
  cleaner: 'Personal de aseo',
  admin: 'Administrador',
}
