import type { ApiResponse } from '~/types';

/**
 * Base API service with common HTTP methods
 * @module services/api
 */

/**
 * Get the API base URL from runtime config
 * @returns {string} The API base URL
 */
function getBaseUrl(): string {
  const config = useRuntimeConfig();
  return config.public.apiBase;
}

/**
 * Make authenticated API request
 * @param {string} endpoint - API endpoint
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<T>} Response data
 * @throws {Error} If request fails
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const userStore = useUserStore();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
    ...options.headers
  };

  const response = await fetch(`${getBaseUrl()}${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * API service with common HTTP methods
 */
export const api = {
  /**
   * GET request
   * @param {string} endpoint - API endpoint
   * @returns {Promise<T>} Response data
   */
  get<T>(endpoint: string): Promise<T> {
    return request<T>(endpoint, { method: 'GET' });
  },

  /**
   * POST request
   * @param {string} endpoint - API endpoint
   * @param {any} data - Request body
   * @returns {Promise<T>} Response data
   */
  post<T>(endpoint: string, data: any): Promise<T> {
    return request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  /**
   * PUT request
   * @param {string} endpoint - API endpoint
   * @param {any} data - Request body
   * @returns {Promise<T>} Response data
   */
  put<T>(endpoint: string, data: any): Promise<T> {
    return request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  /**
   * DELETE request
   * @param {string} endpoint - API endpoint
   * @returns {Promise<T>} Response data
   */
  delete<T>(endpoint: string): Promise<T> {
    return request<T>(endpoint, { method: 'DELETE' });
  }
};


