export type AddressSuggestion = {
  label: string
  name: string
  postcode: string
  city: string
}

export type AddressAutocompleteInputProps = {
  modelValue: string
  placeholder?: string
  inputId?: string
  required?: boolean
  disabled?: boolean
}
