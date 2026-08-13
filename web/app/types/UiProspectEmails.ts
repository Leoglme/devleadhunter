import type { Prospect } from '~/types'

export type UiProspectEmailsProps = {
  prospect: Prospect
  editable: boolean
}

export type UiProspectEmailsEmits = {
  updated: [prospect: Prospect]
}
