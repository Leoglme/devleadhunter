import type { Prospect } from '~/types'

/** Last-column action rendered for each row. */
export type UiProspectTableRowAction = 'delete' | 'remove'

export type UiProspectTableProps = {
  prospects: Prospect[]
  selectedProspects?: string[]
  /** When true, renders the A/B variant column (values keyed by prospect id). */
  showAbVariant?: boolean
  abVariants?: Record<number, string | null | undefined>
  /** Action button behavior in the last column (default: delete icon). */
  rowAction?: UiProspectTableRowAction
  /** Hide the selection checkbox column. */
  hideSelection?: boolean
}

export type UiProspectTableEmits = {
  viewProspect: [prospect: Prospect]
  editProspect: [prospect: Prospect]
  deleteProspect: [prospect: Prospect]
  removeProspect: [prospect: Prospect]
  toggleSelect: [prospect: Prospect]
  toggleSelectAll: [checked: boolean]
}
