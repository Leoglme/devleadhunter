import type { SmsMessage } from '~/services/smsService'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiSmsLogDrawerProps = UiDrawerProps & {
  message?: SmsMessage | null
}

export type UiSmsLogDrawerEmits = {
  close: []
  back: []
  resend: [message: SmsMessage]
}
