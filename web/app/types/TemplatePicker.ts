import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

export type TemplatePickerProps = {
  templates: DemoSiteTemplate[]
  modelValue: string
  theme: DemoSiteTheme
  recommendedTrade?: string | null
  publishedSiteUrl?: string | null
  templatesBelowPreview?: boolean
}

export type TemplateThemeColorKey = keyof DemoSiteTheme

export type TemplatePreviewDevice = 'desktop' | 'mobile'

export type TemplatePickerEmits = {
  'update:modelValue': [value: string]
  'update:theme': [value: DemoSiteTheme]
}
