<template>
  <div v-if="!site" class="flex min-h-screen items-center justify-center text-slate-500">
    Template inconnu : {{ templateId }}
  </div>
  <DemoSiteView v-else :site="site" />
</template>

<script lang="ts" setup>
// Catalogue public des templates : chaque template rendu avec son contenu fictif,
// palette surchargée par query (?primary=&secondary=&accent=). Alimente l'iframe
// d'aperçu du sélecteur de templates et sert d'asset commercial partageable.
import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import previewLayers from '~/utils/previewLayers.json'

/** Flat SiteContents produced by the API pipeline, bundled so they exist on both SSR and client. */
const PREVIEW_SITE_CONTENTS: Record<string, Record<string, unknown>> = previewLayers as Record<
  string,
  Record<string, unknown>
>

const route: ReturnType<typeof useRoute> = useRoute()

const templateId: ComputedRef<string> = computed((): string => String(route.params.templateId ?? ''))

/**
 * Read a palette color override from the query, normalized to `#rrggbb`.
 * @param key - Palette key (`primary`, `secondary` or `accent`).
 * @returns The hex color, or null when absent or invalid.
 */
function paletteOverride(key: string): string | null {
  const raw: unknown = route.query[key]
  if (typeof raw !== 'string') return null
  const hex: string = raw.startsWith('#') ? raw : `#${raw}`
  return /^#[0-9A-Fa-f]{6}$/.test(hex) ? hex : null
}

/** Fake DemoSitePublic in `draft` status, which keeps every tracking path disabled. */
const site: ComputedRef<DemoSitePublic | null> = computed((): DemoSitePublic | null => {
  const previewContent: Record<string, unknown> | undefined = PREVIEW_SITE_CONTENTS[templateId.value]
  if (!previewContent) {
    return null
  }
  const palette: Record<string, unknown> = { ...((previewContent.palette as Record<string, unknown>) ?? {}) }
  for (const key of ['primary', 'secondary', 'accent']) {
    const override: string | null = paletteOverride(key)
    if (override) palette[key] = override
  }
  return {
    slug: `catalog-${templateId.value}`,
    business_name: String(previewContent.businessName ?? 'Aperçu'),
    template_id: templateId.value,
    content_json: { ...previewContent, palette },
    status: 'draft',
    storyblok_preview_token: null,
    storyblok_region: null,
  }
})

useSeoMeta({
  title: (): string => (site.value ? `Aperçu — ${site.value.business_name}` : 'Template inconnu'),
  robots: 'noindex, follow',
})
</script>
