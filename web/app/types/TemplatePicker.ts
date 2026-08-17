import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

export type TemplatePickerProps = {
  templates: DemoSiteTemplate[]
  modelValue: string
  theme: DemoSiteTheme
  recommendedTrade?: string | null
  publishedSiteUrl?: string | null
  /** Bump to force the live preview iframe to reload (the published URL itself doesn't change). */
  reloadNonce?: number
  templatesBelowPreview?: boolean
  /** Action colour = the prospect logo (true) or the template default (false). Null hides the Logo/Template picker (wizard). */
  useBrandColor?: boolean | null
  /** The colour extracted from the prospect logo, for the "Logo" pill. Null = no usable logo colour. */
  brandColor?: string | null
}

export type TemplateThemeColorKey = keyof DemoSiteTheme

export type TemplatePreviewDevice = 'desktop' | 'mobile'

export type TemplatePickerEmits = {
  'update:modelValue': [value: string]
  'update:theme': [value: DemoSiteTheme]
  'update:useBrandColor': [value: boolean]
}
