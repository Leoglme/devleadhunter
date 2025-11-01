/**
 * Authentication middleware
 * Protects routes that require authentication
 * @module middleware/auth
 */

export default defineNuxtRouteMiddleware((to) => {
  /**
   * User store
   */
  const userStore = useUserStore();

  /**
   * Check if user is authenticated
   */
  if (!userStore.isAuthenticated) {
    return navigateTo('/login');
  }
});


