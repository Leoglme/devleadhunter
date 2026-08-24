import type { EmailLog } from '~/types'

/** Props of the failed-email resend sub-drawer. */
export type EmailResendDrawerProps = {
  open: boolean
  log: EmailLog | null
  showBack: boolean
}
