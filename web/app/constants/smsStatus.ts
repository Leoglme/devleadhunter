import type { SmsStatus } from '~/services/smsService'

/** Human label for each SMS lifecycle status. */
export const SMS_STATUS_LABELS: Record<SmsStatus, string> = {
  pending: 'En attente',
  sent: 'Envoyé',
  delivered: 'Délivré',
  failed: 'Échoué',
}

/** Badge modifier class for each SMS lifecycle status. */
export const SMS_STATUS_BADGE_CLASS: Record<SmsStatus, string> = {
  pending: 'app-badge--progress',
  sent: 'app-badge--info',
  delivered: 'app-badge--success',
  failed: 'app-badge--danger',
}
