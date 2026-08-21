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
  label?: string
}
