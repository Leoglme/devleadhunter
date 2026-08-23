import type { EmailStatus } from '~/types'

export type EmailStatusBadgeProps = {
  status: EmailStatus
  count?: number
}

export type EmailStatusPresentation = {
  label: string
  icon: string
  variant: string
  spin?: boolean
}
