import type { CampaignFormDrawerMode } from '~/types/DrawerStack'
import type { CampaignDetailResponse } from '~/services/campaignService'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiCampaignDrawerProps = UiDrawerProps & {
  mode?: CampaignFormDrawerMode
  campaign?: CampaignDetailResponse | null
}

/** Local shape of the campaign form; the A/B templates are only asked on creation. */
export type CampaignForm = {
  name: string
  description: string
  templateIdA: number
  templateIdB: number
}

export type UiCampaignDrawerEmits = {
  close: []
  back: []
  saved: []
}
