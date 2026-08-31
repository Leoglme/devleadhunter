import type { NotificationLevel } from '~/services/notificationsService'
import type { NotificationLevelPresentation } from '~/types/UiNotificationList'

/** Icon + colored tile for each notification level (history list + detail view). */
export const NOTIFICATION_LEVEL_PRESENTATION: Record<NotificationLevel, NotificationLevelPresentation> = {
  info: { icon: 'i-lucide-info', tile: 'bg-[var(--app-blue-soft)] text-[var(--app-blue)]' },
  success: { icon: 'i-lucide-check', tile: 'bg-[var(--app-green-soft)] text-[var(--app-green)]' },
  warning: { icon: 'i-lucide-triangle-alert', tile: 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]' },
  error: { icon: 'i-lucide-circle-alert', tile: 'bg-[var(--app-red-soft)] text-[var(--app-red)]' },
}

/**
 * Icon + tile classes for a notification level (falls back to info).
 * @param level - The notification level.
 * @returns The presentation for that level.
 */
export function notificationPresentation(level: NotificationLevel): NotificationLevelPresentation {
  return NOTIFICATION_LEVEL_PRESENTATION[level] ?? NOTIFICATION_LEVEL_PRESENTATION.info
}
