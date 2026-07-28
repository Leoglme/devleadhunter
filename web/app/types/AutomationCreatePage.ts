import type { AutomationMode } from '~/types/Automation'
import type { DemoSiteTheme } from '~/services/demoSiteService'

/** Stable identity of a wizard step, independent of its visible position. */
export type AutomationStepKey = 'target' | 'site' | 'emails' | 'launch'

export type AutomationStepDefinition = {
  key: AutomationStepKey
  label: string
  hint: string
}

/** Back link of the tunnel header, pointing at the section it was opened from. */
export type AutomationOriginLink = {
  to: string
  label: string
}

export type AutomationRecapRow = {
  label: string
  value: string
  icon: string
  detail?: string
}

/** Tunnel state persisted in sessionStorage so leaving the page loses nothing. */
export type AutomationDraft = {
  form: TunnelForm
  selectedProspectIds: string[]
  currentStep: number
  hasPickedTemplate: boolean
}

export type TunnelForm = {
  name: string
  mode: AutomationMode
  templateId: string
  theme: DemoSiteTheme
  autoCampaign: boolean
  emailA: number
  emailB: number
  metiers: string
  villes: string
  targetDays: number
  onlyWithoutWebsite: boolean
}
