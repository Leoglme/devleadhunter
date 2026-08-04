import type { DemoSite } from '~/services/demoSiteService'

export type DemoSiteCardProps = {
  site: DemoSite
  templateName: string | null
}

export type DemoSiteCardEmits = {
  copy: [url: string]
  open: [url: string]
}
