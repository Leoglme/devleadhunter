export type BaseTableAlign = 'left' | 'center' | 'right'

export type BaseTableProps = {
  minWidth?: string
}

export type BaseTableThProps = {
  align?: BaseTableAlign
  srOnly?: boolean
}

export type BaseTableTdProps = {
  align?: BaseTableAlign
  /** Column name shown before the value once the row collapses into a card (< md). */
  label?: string
}
