/** Editable credit pricing form of the admin credit-settings page. */
export type CreditSettingsForm = {
  price_per_credit: number
  credits_per_search: number
  credits_per_result: number
  credits_per_email: number
  free_credits_on_signup: number
  minimum_credits_purchase: number
}
