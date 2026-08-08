import type { AddressSuggestion } from '~/types/AddressAutocompleteInput'

export type UiAddressAutocompleteInputEmits = {
  'update:modelValue': [value: string]
  select: [suggestion: AddressSuggestion]
}
