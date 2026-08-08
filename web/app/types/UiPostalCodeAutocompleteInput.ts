import type { PostalCodeCitySuggestion } from '~/types/PostalCodeAutocompleteInput'

export type UiPostalCodeAutocompleteInputEmits = {
  'update:modelValue': [value: string]
  select: [suggestion: PostalCodeCitySuggestion]
}
