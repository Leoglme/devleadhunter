/**
 * Super-admin middleware
 * Protects routes reserved to the platform owner (SUPER_ADMIN only).
 * @module middleware/super-admin
 */

import { isSuperAdmin } from '~/utils/userRoles'

export default defineNuxtRouteMiddleware(async () => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()

  if (import.meta.client) {
    if (!userStore.isAuthenticated) {
      userStore.initializeAuth()
    }

    const isValid: boolean = await userStore.validateAuth()
    if (!isValid) {
      return navigateTo('/login')
    }

    if (!isSuperAdmin(userStore.user?.role)) {
      return navigateTo('/dashboard')
    }
  }
})
