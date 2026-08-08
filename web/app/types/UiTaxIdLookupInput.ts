import type { CompanyBillingPrefill } from '~/types/CompanyRegistryLookup'

export type UiTaxIdLookupInputEmits = {
  'update:modelValue': [value: string]
  prefill: [prefill: CompanyBillingPrefill]
}
