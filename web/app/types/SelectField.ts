/** What a select entry can carry — labels are strings, ids are numbers. */
export type SelectFieldValue = string | number

export type SelectFieldOption<TValue extends SelectFieldValue = string> = {
  value: TValue
  label: string
}

export type SelectFieldProps<TValue extends SelectFieldValue = string> = {
  options: SelectFieldOption<TValue>[]
  placeholder?: string
  disabled?: boolean
}
