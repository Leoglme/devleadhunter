/** Props for the drawer that attaches existing prospects to a campaign. */
export type UiCampaignProspectsPickerDrawerProps = {
  open: boolean
  showBack?: boolean
  campaignId: number | null
  existingProspectIds: number[]
}

export type UiCampaignProspectsPickerDrawerEmits = {
  close: []
  back: []
  added: []
}
