/**
 * Toast notification composable
 * @module composables/useToast
 */

interface ToastOptions {
  duration?: number;
  type?: 'success' | 'error' | 'info' | 'warning';
}

/**
 * Use toast notification
 * @returns {object} Toast methods
 * @example
 * ```typescript
 * const toast = useToast();
 * toast.success('Operation successful');
 * toast.error('Operation failed');
 * ```
 */
export function useToast() {
  const showToast = (message: string, options: ToastOptions = {}) => {
    // Skip on server-side rendering
    if (process.server || !process.client) {
      return;
    }
    
    // This is a simplified implementation
    // In production, you'd use a proper toast library like vue-toastification
    
    const { type = 'info', duration = 3000 } = options;
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
      type === 'success' ? 'bg-green-600' :
      type === 'error' ? 'bg-red-600' :
      type === 'warning' ? 'bg-yellow-600' :
      'bg-blue-600'
    } text-white`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Remove toast after duration
    setTimeout(() => {
      toast.remove();
    }, duration);
  };

  return {
    success: (message: string) => showToast(message, { type: 'success' }),
    error: (message: string) => showToast(message, { type: 'error' }),
    info: (message: string) => showToast(message, { type: 'info' }),
    warning: (message: string) => showToast(message, { type: 'warning' })
  };
}

