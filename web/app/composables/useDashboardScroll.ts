import type { UseDashboardScrollReturn } from '~/types/Composables'

export const DASHBOARD_SCROLL_CONTAINER_ID: string = 'dashboard-scroll'

/**
 * Scroll the dashboard shell, whose scrolling element is the layout's <main>, not the window.
 * @returns Scroll helpers targeting that container.
 */
export function useDashboardScroll(): UseDashboardScrollReturn {
  /**
   * Resolve the scrolling element of the dashboard layout.
   * @returns The container, or null when the layout is not mounted.
   */
  function resolveContainer(): HTMLElement | null {
    if (!import.meta.client) {
      return null
    }
    return document.getElementById(DASHBOARD_SCROLL_CONTAINER_ID)
  }

  /**
   * Scroll the dashboard content back to its top.
   * @param behavior - Scroll behavior, smooth by default.
   */
  function scrollToTop(behavior: ScrollBehavior = 'smooth'): void {
    resolveContainer()?.scrollTo({ top: 0, behavior })
  }

  /**
   * Scroll the dashboard content down to its bottom.
   * @param behavior - Scroll behavior, smooth by default.
   */
  function scrollToBottom(behavior: ScrollBehavior = 'smooth'): void {
    const container: HTMLElement | null = resolveContainer()
    container?.scrollTo({ top: container.scrollHeight, behavior })
  }

  return { scrollToTop, scrollToBottom }
}
