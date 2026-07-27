<template>
  <div class="@container">
    <input ref="colorInputRef" type="color" class="sr-only" :value="theme[activeColorKey]" @input="onColorInput" />

    <div class="grid gap-4 @3xl:grid-cols-[280px_minmax(0,1fr)]">
      <div
        class="flex gap-2 overflow-x-auto pb-1 @3xl:max-h-[560px] @3xl:flex-col @3xl:overflow-x-visible @3xl:overflow-y-auto @3xl:pr-1 @3xl:pb-0"
      >
        <button
          v-for="template in sortedTemplates"
          :key="template.id"
          type="button"
          :class="[
            'w-56 shrink-0 rounded-xl border p-2 text-left transition-colors @3xl:w-full',
            modelValue === template.id
              ? 'border-[var(--app-ink)] bg-[var(--app-surface)] ring-1 ring-[var(--app-ink)]/15'
              : 'border-[var(--app-line)] bg-[var(--app-surface)] hover:border-[var(--app-ink-soft)]',
          ]"
          @click="selectTemplate(template)"
        >
          <div class="relative aspect-[16/10] overflow-hidden rounded-lg border border-[var(--app-line)]">
            <img
              v-if="!failedThumbnails.has(template.id)"
              :src="thumbnailUrl(template.id)"
              :alt="`Aperçu du template ${template.name}`"
              class="absolute inset-0 h-full w-full object-cover object-top"
              loading="lazy"
              @error="failedThumbnails.add(template.id)"
            />
            <div v-else class="absolute inset-0" :style="{ background: fallbackGradient(template) }"></div>
            <span
              v-if="modelValue === template.id"
              class="absolute top-1.5 right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--app-ink)] text-[var(--app-bg)]"
            >
              <UIcon name="i-lucide-check" class="h-3 w-3" />
            </span>
          </div>
          <div class="mt-2 flex items-center justify-between gap-2 px-0.5 pb-0.5">
            <span class="truncate text-[13px] font-semibold text-[var(--app-ink)]">{{ template.name }}</span>
            <span
              v-if="isRecommended(template)"
              class="shrink-0 rounded-full bg-[var(--app-accent-soft)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-accent-ink)]"
            >
              Recommandé
            </span>
          </div>
        </button>
      </div>

      <div v-if="selectedTemplate" class="app-card self-start overflow-hidden">
        <div
          ref="previewContainer"
          :class="[
            'relative aspect-[16/10] overflow-hidden border-b border-[var(--app-line)]',
            isLivePreview && previewDevice === 'mobile' ? 'bg-[var(--app-surface-2)]' : '',
          ]"
        >
          <template v-if="isLivePreview">
            <iframe
              :src="livePreviewUrl"
              :class="[
                'absolute top-0 origin-top-left border-0 bg-white',
                previewDevice === 'mobile'
                  ? 'h-[844px] w-[390px] rounded-xl shadow-[var(--app-shadow-soft)]'
                  : 'left-0 h-[800px] w-[1280px]',
              ]"
              :style="liveFrameStyle"
              title="Aperçu interactif du template"
              @load="endPreviewLoad"
            />
          </template>
          <template v-else>
            <img
              v-if="!failedThumbnails.has(selectedTemplate.id)"
              :src="thumbnailUrl(selectedTemplate.id)"
              :alt="`Aperçu du template ${selectedTemplate.name}`"
              class="absolute inset-0 h-full w-full object-cover object-top"
            />
            <div v-else class="absolute inset-0" :style="{ background: fallbackGradient(selectedTemplate) }"></div>
          </template>

          <Transition name="preview-veil">
            <div
              v-if="isLivePreview && isPreviewLoading"
              class="absolute inset-0 flex flex-col items-center justify-center gap-3.5 bg-[var(--app-surface)]"
            >
              <div class="loader-smooth"></div>
              <span class="text-xs text-[var(--app-ink-soft)]">Chargement de l'aperçu…</span>
            </div>
          </Transition>

          <div
            v-if="isLivePreview"
            class="absolute top-3 right-3 flex overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] shadow-[var(--app-shadow-soft)]"
          >
            <button
              type="button"
              title="Aperçu ordinateur"
              :class="deviceButtonClass('desktop')"
              @click="previewDevice = 'desktop'"
            >
              <UIcon name="i-lucide-monitor" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="Aperçu mobile"
              :class="deviceButtonClass('mobile')"
              @click="previewDevice = 'mobile'"
            >
              <UIcon name="i-lucide-smartphone" class="h-3.5 w-3.5" />
            </button>
          </div>

          <div class="absolute right-3 bottom-3 flex gap-2">
            <button
              type="button"
              class="app-btn-secondary h-8 px-3 text-xs shadow-[var(--app-shadow-soft)]"
              @click="toggleLivePreview"
            >
              <UIcon :name="isLivePreview ? 'i-lucide-image' : 'i-lucide-play'" class="h-3.5 w-3.5" />
              {{ isLivePreview ? 'Image' : 'Aperçu live' }}
            </button>
            <a
              :href="livePreviewUrl"
              target="_blank"
              rel="noopener"
              class="app-btn-secondary h-8 px-3 text-xs shadow-[var(--app-shadow-soft)]"
              title="Ouvrir l'aperçu dans un nouvel onglet"
            >
              <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
            </a>
          </div>
        </div>

        <div class="space-y-4 p-5">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <p class="font-semibold text-[var(--app-ink)]">{{ selectedTemplate.name }}</p>
              <span
                v-if="isRecommended(selectedTemplate)"
                class="rounded-full bg-[var(--app-accent-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--app-accent-ink)]"
              >
                Recommandé pour {{ recommendedTrade }}
              </span>
            </div>
            <p class="mt-1.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">{{ selectedTemplate.description }}</p>
          </div>

          <div class="border-t border-[var(--app-line-soft)] pt-4">
            <div class="mb-2.5 flex items-center justify-between">
              <p class="app-label">Couleurs du site</p>
              <button
                v-if="isThemeCustomised"
                type="button"
                class="cursor-pointer text-[11px] font-medium text-[var(--app-ink-soft)] underline underline-offset-2 hover:text-[var(--app-ink)]"
                @click="resetTheme"
              >
                Revenir aux couleurs du template
              </button>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <div v-for="colorKey in colorKeys" :key="colorKey">
                <span class="mb-1 block text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">
                  {{ colorLabels[colorKey] }}
                </span>
                <div class="flex items-center gap-1.5">
                  <button
                    type="button"
                    :title="`Choisir la couleur ${colorLabels[colorKey].toLowerCase()}`"
                    class="h-8 w-8 shrink-0 cursor-pointer rounded-lg border border-[var(--app-line)] transition-transform hover:scale-105"
                    :style="{ backgroundColor: theme[colorKey] }"
                    @click="openColorPicker(colorKey)"
                  />
                  <input
                    :value="theme[colorKey]"
                    type="text"
                    class="input-field h-8 min-w-0 text-xs"
                    placeholder="#1d4ed8"
                    maxlength="7"
                    @input="updateThemeColor(colorKey, ($event.target as HTMLInputElement).value)"
                  />
                </div>
              </div>
            </div>
            <p class="mt-2.5 flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
              <UIcon name="i-lucide-info" class="h-3 w-3 shrink-0" />
              L'aperçu est interactif : vos couleurs s'y appliquent en direct.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type {
  TemplatePickerEmits,
  TemplatePickerProps,
  TemplatePreviewDevice,
  TemplateThemeColorKey,
} from '~/types/TemplatePicker'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

/** Template picker: compact list, real screenshot, live iframe preview with theme colors applied. */
const props: TemplatePickerProps = defineProps({
  templates: {
    type: Array as PropType<DemoSiteTemplate[]>,
    required: true,
  },
  modelValue: {
    type: String,
    required: true,
  },
  theme: {
    type: Object as PropType<DemoSiteTheme>,
    required: true,
  },
  recommendedTrade: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const emit: EmitFn<TemplatePickerEmits> = defineEmits<TemplatePickerEmits>()

const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const colorKeys: TemplateThemeColorKey[] = ['primary', 'secondary', 'accent']
const colorLabels: Record<TemplateThemeColorKey, string> = {
  primary: 'Principale',
  secondary: 'Fond',
  accent: 'Accent',
}

/** Native viewport of the live iframe per device (scaled down to fit the pane). */
const LIVE_VIEWPORTS: Record<TemplatePreviewDevice, { width: number; height: number }> = {
  desktop: { width: 1280, height: 800 },
  mobile: { width: 390, height: 844 },
}

const colorInputRef: Ref<HTMLInputElement | null> = ref(null)
const activeColorKey: Ref<TemplateThemeColorKey> = ref('primary')
const previewContainer: Ref<HTMLElement | null> = ref(null)
const paneWidth: Ref<number> = ref(640)
const paneHeight: Ref<number> = ref(400)
const isLivePreview: Ref<boolean> = ref(true)
const previewDevice: Ref<TemplatePreviewDevice> = ref('desktop')
const livePreviewUrl: Ref<string> = ref('')
const isPreviewLoading: Ref<boolean> = ref(true)
const failedThumbnails: Ref<Set<string>> = ref(new Set())

/** ResizeObserver keeping the scaled iframe in sync with the preview pane width. */
let previewResizeObserver: ResizeObserver | null = null
/** Timer debouncing live preview reloads while colors are edited. */
let livePreviewReloadTimer: ReturnType<typeof setTimeout> | null = null
/** Timer lifting the loading veil when the iframe never reports a load. */
let previewLoadTimeoutTimer: ReturnType<typeof setTimeout> | null = null

/** The template currently selected in the list. */
const selectedTemplate: ComputedRef<DemoSiteTemplate | null> = computed(
  (): DemoSiteTemplate | null =>
    props.templates.find((template: DemoSiteTemplate): boolean => template.id === props.modelValue) ?? null,
)

/** Templates with the ones recommended for the targeted trade bubbled to the top. */
const sortedTemplates: ComputedRef<DemoSiteTemplate[]> = computed((): DemoSiteTemplate[] => {
  if (!props.recommendedTrade) return props.templates
  const recommended: DemoSiteTemplate[] = props.templates.filter((template: DemoSiteTemplate): boolean =>
    isRecommended(template),
  )
  const others: DemoSiteTemplate[] = props.templates.filter(
    (template: DemoSiteTemplate): boolean => !isRecommended(template),
  )
  return [...recommended, ...others]
})

/** Scaled position of the live iframe: full-width desktop, or a centered phone. */
const liveFrameStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const viewport: { width: number; height: number } = LIVE_VIEWPORTS[previewDevice.value]
  if (previewDevice.value === 'mobile') {
    const scale: number = paneHeight.value / viewport.height
    return {
      transform: `scale(${scale})`,
      left: `calc(50% - ${(viewport.width * scale) / 2}px)`,
    }
  }
  return { transform: `scale(${paneWidth.value / viewport.width})` }
})

/** Whether the current theme differs from the selected template's defaults. */
const isThemeCustomised: ComputedRef<boolean> = computed((): boolean => {
  const defaults: DemoSiteTheme | undefined = selectedTemplate.value?.default_theme
  if (!defaults) return false
  return colorKeys.some((key: TemplateThemeColorKey): boolean => defaults[key] !== props.theme[key])
})

/**
 * Lowercase a trade string and strip its accents for keyword matching.
 * @param value - Raw trade or category label.
 * @returns The normalized string.
 */
function normalizeTrade(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
}

/**
 * Whether a template targets the trade the picker recommends for.
 * @param template - Template to test.
 * @returns True when one of the template's trade keywords matches.
 */
function isRecommended(template: DemoSiteTemplate): boolean {
  if (!props.recommendedTrade) return false
  const trade: string = normalizeTrade(props.recommendedTrade)
  if (!trade) return false
  return (template.trades ?? []).some((keyword: string): boolean => {
    const normalized: string = normalizeTrade(keyword)
    return trade.includes(normalized) || normalized.includes(trade)
  })
}

/**
 * Static screenshot path of a template (bundled with the app).
 * @param templateId - Template identifier.
 * @returns The public thumbnail URL.
 */
function thumbnailUrl(templateId: string): string {
  return `/templates/${templateId}.jpg`
}

/**
 * Gradient used when a template has no screenshot yet.
 * @param template - Template whose default theme feeds the gradient.
 * @returns A CSS gradient string.
 */
function fallbackGradient(template: DemoSiteTemplate): string {
  return `linear-gradient(135deg, ${template.default_theme.secondary} 0%, ${template.default_theme.primary} 100%)`
}

/**
 * Build the demo-host catalog URL for a template, with the current colors applied.
 * @param template - Template to preview.
 * @returns The catalog page URL.
 */
function buildLivePreviewUrl(template: DemoSiteTemplate): string {
  const base: string = String(config.public.demoHostBase).replace(/\/$/, '')
  const params: URLSearchParams = new URLSearchParams()
  for (const key of colorKeys) {
    const color: string = props.modelValue === template.id ? props.theme[key] : template.default_theme[key]
    params.set(key, color.replace('#', ''))
  }
  return `${base}/t/${template.id}?${params.toString()}`
}

/**
 * Point the live iframe at the selected template with the current colors.
 */
function applyLivePreviewUrl(): void {
  if (selectedTemplate.value) livePreviewUrl.value = buildLivePreviewUrl(selectedTemplate.value)
}

/**
 * Refresh the live iframe URL, debounced so hex typing doesn't reload on every keystroke.
 */
function scheduleLivePreviewReload(): void {
  if (livePreviewReloadTimer) clearTimeout(livePreviewReloadTimer)
  livePreviewReloadTimer = setTimeout(applyLivePreviewUrl, 600)
}

/**
 * Cover the preview until the iframe reports its document is ready.
 */
function beginPreviewLoad(): void {
  isPreviewLoading.value = true
  if (previewLoadTimeoutTimer) clearTimeout(previewLoadTimeoutTimer)
  // An unreachable demo-host never fires load: never leave the veil spinning for good.
  previewLoadTimeoutTimer = setTimeout((): void => {
    isPreviewLoading.value = false
  }, 8000)
}

/**
 * Lift the loading veil once the iframe finished loading.
 */
function endPreviewLoad(): void {
  if (previewLoadTimeoutTimer) clearTimeout(previewLoadTimeoutTimer)
  isPreviewLoading.value = false
}

/**
 * Toggle between the static screenshot and the live iframe.
 */
function toggleLivePreview(): void {
  isLivePreview.value = !isLivePreview.value
}

/**
 * Classes of a device toggle button (active device highlighted).
 * @param device - The device the button switches to.
 * @returns Button classes.
 */
function deviceButtonClass(device: TemplatePreviewDevice): string {
  const base: string = 'flex h-8 w-9 cursor-pointer items-center justify-center transition-colors'
  if (previewDevice.value === device) {
    return `${base} bg-[var(--app-ink)] text-[var(--app-bg)]`
  }
  return `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Select a template and sync its default theme.
 * @param template - Template picked in the list.
 */
function selectTemplate(template: DemoSiteTemplate): void {
  emit('update:modelValue', template.id)
  emit('update:theme', { ...template.default_theme })
}

/**
 * Reset the theme to the selected template's default colors.
 */
function resetTheme(): void {
  const defaults: DemoSiteTheme | undefined = selectedTemplate.value?.default_theme
  if (defaults) emit('update:theme', { ...defaults })
}

/**
 * Open the native color picker for a theme key.
 * @param colorKey - Theme key being edited.
 */
function openColorPicker(colorKey: TemplateThemeColorKey): void {
  activeColorKey.value = colorKey
  nextTick((): void => {
    colorInputRef.value?.click()
  })
}

/**
 * Handle a color input change from the hidden native picker.
 * @param event - Input event of the hidden color input.
 */
function onColorInput(event: Event): void {
  updateThemeColor(activeColorKey.value, (event.target as HTMLInputElement).value)
}

/**
 * Update a single theme color when the hex value is valid, and show it live.
 * @param key - Theme key being edited.
 * @param value - Candidate hex color.
 */
function updateThemeColor(key: TemplateThemeColorKey, value: string): void {
  if (!/^#[0-9A-Fa-f]{6}$/.test(value)) return
  emit('update:theme', { ...props.theme, [key]: value })
  isLivePreview.value = true
}

watch(
  (): string => props.modelValue,
  (): void => {
    isLivePreview.value = true
    beginPreviewLoad()
    applyLivePreviewUrl()
  },
  { immediate: true },
)

watch((): DemoSiteTheme => props.theme, scheduleLivePreviewReload, { deep: true })

watch([livePreviewUrl, isLivePreview], (): void => {
  if (isLivePreview.value) beginPreviewLoad()
})

// The detail pane mounts only once templates are loaded: follow the element, not onMounted.
watch(previewContainer, (element: HTMLElement | null): void => {
  previewResizeObserver?.disconnect()
  if (element) previewResizeObserver?.observe(element)
})

onMounted((): void => {
  previewResizeObserver = new ResizeObserver((entries: ResizeObserverEntry[]): void => {
    const rect: DOMRectReadOnly | undefined = entries[0]?.contentRect
    if (rect && rect.width > 0) {
      paneWidth.value = rect.width
      paneHeight.value = rect.height
    }
  })
  if (previewContainer.value) previewResizeObserver.observe(previewContainer.value)
})

onBeforeUnmount((): void => {
  previewResizeObserver?.disconnect()
  if (livePreviewReloadTimer) clearTimeout(livePreviewReloadTimer)
  if (previewLoadTimeoutTimer) clearTimeout(previewLoadTimeoutTimer)
})
</script>

<style scoped>
.preview-veil-leave-active {
  transition: opacity 0.2s ease;
}
.preview-veil-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .preview-veil-leave-active {
    transition: none;
  }
}
</style>
