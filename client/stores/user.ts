import { defineStore } from 'pinia';
import type { User, LoginCredentials, SignupData } from '~/types';
import type { Ref } from 'vue';
import { ref, computed } from 'vue';

/**
 * Pinia store for user authentication and profile management
 * @module stores/user
 */

interface UserState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
}

/**
 * User store definition
 */
export const useUserStore = defineStore('user', () => {
  // State
  const user: Ref<User | null> = ref(null);
  const token: Ref<string | null> = ref(null);
  const isLoading: Ref<boolean> = ref(false);
  const error: Ref<string | null> = ref(null);

  // Getters
  const isAuthenticated = computed(() => {
    return user.value !== null && token.value !== null;
  });

  const userName = computed(() => {
    return user.value?.name ?? '';
  });

  const userEmail = computed(() => {
    return user.value?.email ?? '';
  });

  /**
   * Login user with credentials
   * @param {LoginCredentials} credentials - Login credentials
   * @returns {Promise<void>} Promise that resolves when login is complete
   * @throws {Error} If login fails
   * 
   * @example
   * ```typescript
   * await userStore.login({ email: 'user@example.com', password: 'password' });
   * ```
   */
  async function login(credentials: LoginCredentials): Promise<void> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock user data
      const mockUser = {
        id: '1',
        name: 'John Doe',
        email: credentials.email,
        createdAt: new Date().toISOString()
      };
      
      user.value = mockUser;
      token.value = 'mock-jwt-token-' + Date.now();
      
      // Store token in localStorage
      if (process.client) {
        localStorage.setItem('token', token.value);
        localStorage.setItem('user', JSON.stringify(user.value));
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Login failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const response = await $fetch('/api/auth/login', {
    //   method: 'POST',
    //   body: credentials
    // });
  }

  /**
   * Signup new user
   * @param {SignupData} data - Signup data
   * @returns {Promise<void>} Promise that resolves when signup is complete
   * @throws {Error} If signup fails
   * 
   * @example
   * ```typescript
   * await userStore.signup({ 
   *   name: 'John Doe', 
   *   email: 'john@example.com', 
   *   password: 'password' 
   * });
   * ```
   */
  async function signup(data: SignupData): Promise<void> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock user data
      const mockUser = {
        id: '1',
        name: data.name,
        email: data.email,
        createdAt: new Date().toISOString()
      };
      
      user.value = mockUser;
      token.value = 'mock-jwt-token-' + Date.now();
      
      // Store token in localStorage
      if (process.client) {
        localStorage.setItem('token', token.value);
        localStorage.setItem('user', JSON.stringify(user.value));
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Signup failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const response = await $fetch('/api/auth/signup', {
    //   method: 'POST',
    //   body: data
    // });
  }

  /**
   * Logout current user
   * @returns {void}
   */
  function logout(): void {
    user.value = null;
    token.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  /**
   * Update user profile
   * @param {Partial<User>} data - Updated user data
   * @returns {Promise<void>} Promise that resolves when update is complete
   * @throws {Error} If update fails
   */
  async function updateProfile(data: Partial<User>): Promise<void> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      if (user.value) {
        user.value = { ...user.value, ...data };
        if (process.client) {
          localStorage.setItem('user', JSON.stringify(user.value));
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Profile update failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const response = await $fetch('/api/auth/profile', {
    //   method: 'PUT',
    //   headers: { Authorization: `Bearer ${token.value}` },
    //   body: data
    // });
  }

  /**
   * Initialize user from localStorage
   * @returns {void}
   */
  function initializeAuth(): void {
    if (process.client) {
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');
      
      if (storedToken && storedUser) {
        token.value = storedToken;
        user.value = JSON.parse(storedUser);
      }
    }
  }

  // Initialize on store creation
  if (process.client) {
    initializeAuth();
  }

  return {
    // State
    user,
    token,
    isLoading,
    error,
    // Getters
    isAuthenticated,
    userName,
    userEmail,
    // Actions
    login,
    signup,
    logout,
    updateProfile,
    initializeAuth
  };
});

