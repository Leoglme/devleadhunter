import type { Prospect } from '~/types'
import type { SendSmsPrefill } from '~/types/DrawerStack'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiSendSmsDrawerProps = UiDrawerProps & {
  prospect?: Prospect | null
  prefill?: SendSmsPrefill | null
}

/** Local shape of the manual SMS form. */
export type SendSmsForm = {
  to: string
  recipient_name: string
  text: string
}

export type UiSendSmsDrawerEmits = {
  close: []
  back: []
  sent: []
}
