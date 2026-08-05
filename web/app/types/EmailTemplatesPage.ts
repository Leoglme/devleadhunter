import type { EmailTemplate } from '~/types'

/** One collapsible card of the templates page — a theme, or the archived bucket. */
export type TemplateGroup = {
  key: string
  heading: string
  icon: string
  defaultOpen: boolean
  templates: EmailTemplate[]
}
