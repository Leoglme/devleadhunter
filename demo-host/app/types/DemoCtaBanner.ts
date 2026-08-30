import type { DemoSitePublic } from '~/types/demoSite'

/** Props of the « Ce site vous plaît ? » lead banner shown on live demo pages. */
export type DemoCtaBannerProps = {
  site: DemoSitePublic
}

/** Display states of the banner. */
export type DemoCtaBannerState = 'collapsed' | 'open' | 'sent'
