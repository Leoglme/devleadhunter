<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Loading demo site…
  </div>
  <div v-else-if="error || !site" class="flex min-h-screen items-center justify-center bg-slate-950 text-red-300">
    Demo site not found or expired.
  </div>
  <main v-else class="min-h-screen bg-white text-slate-900">
    <DemoSiteView :site="site" />
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

const {
  data: site,
  pending,
  error,
}: Awaited<ReturnType<typeof useAsyncData<DemoSitePublic | undefined>>> = await useAsyncData<DemoSitePublic>(
  () => `demo-site-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

useSeoMeta({
  title: () => site.value?.business_name ?? 'Demo site',
})

/**
 * Choisit une couleur de texte lisible (blanc ou encre) sur un fond hex donné.
 * @param background Couleur de fond au format `#rrggbb`
 * @returns `#111111` sur fond clair, sinon `#ffffff`
 */
function readableTextColor(background: string): string {
  const hex: string = background.replace('#', '')
  if (hex.length !== 6) {
    return '#ffffff'
  }
  const r: number = parseInt(hex.slice(0, 2), 16)
  const g: number = parseInt(hex.slice(2, 4), 16)
  const b: number = parseInt(hex.slice(4, 6), 16)
  const luminance: number = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.6 ? '#111111' : '#ffffff'
}

/**
 * Favicon propre au site : le logo du prospect s'il existe, sinon une pastille
 * SVG « initiale + couleur de marque » — jamais le favicon placeholder générique.
 */
const faviconHref: ComputedRef<string> = computed((): string => {
  const content: Record<string, unknown> = (site.value?.content_json ?? {}) as Record<string, unknown>
  const logo: string = typeof content.logo === 'string' ? content.logo.trim() : ''
  if (logo) {
    return logo
  }
  const palette: Record<string, unknown> = (content.palette ?? {}) as Record<string, unknown>
  const background: string =
    typeof palette.primary === 'string' && palette.primary.trim() ? palette.primary.trim() : '#111111'
  const name: string = site.value?.business_name ?? ''
  const initial: string = (name.match(/[a-z0-9]/i)?.[0] ?? '●').toUpperCase()
  const svg: string =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">` +
    `<rect width="64" height="64" rx="14" fill="${background}"/>` +
    `<text x="32" y="34" dominant-baseline="central" text-anchor="middle" ` +
    `font-family="Arial, Helvetica, sans-serif" font-size="34" font-weight="700" ` +
    `fill="${readableTextColor(background)}">${initial}</text></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
})

useHead(() => ({
  link: [{ key: 'favicon', rel: 'icon', href: faviconHref.value }],
}))
</script>
