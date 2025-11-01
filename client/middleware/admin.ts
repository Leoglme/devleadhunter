/**
 * Admin middleware
 * Protects routes that require admin role
 * @module middleware/admin
 */

export default defineNuxtRouteMiddleware((to) => {
  /**
   * User store
   */
  const userStore = useUserStore();

  /**
   * Check if user is authenticated and is admin
   */
  if (!userStore.isAuthenticated || userStore.user?.role !== 'ADMIN') {
    return navigateTo('/dashboard');
  }
});

