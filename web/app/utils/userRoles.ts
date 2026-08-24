import type { UserRole } from '~/types'

/** Platform owner — full administration. */
export function isSuperAdmin(role: string | undefined | null): boolean {
  return role === 'SUPER_ADMIN'
}

/** Operator — unlimited credits, monitoring/storage, support desk. */
export function isPlatformAdmin(role: string | undefined | null): boolean {
  return role === 'ADMIN' || role === 'SUPER_ADMIN'
}

/** Human label for a role badge. */
export function roleLabel(role: UserRole | string): string {
  switch (role) {
    case 'SUPER_ADMIN':
      return 'Super administrateur'
    case 'ADMIN':
      return 'Administrateur'
    default:
      return 'Utilisateur'
  }
}
