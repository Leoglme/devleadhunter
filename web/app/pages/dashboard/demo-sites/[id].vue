<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
      <NuxtLink to="/dashboard/demo-sites" class="app-btn-secondary w-fit">
        <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
        Retour aux sites
      </NuxtLink>
      <div class="flex flex-wrap gap-2">
        <button v-if="openUrl" type="button" class="app-btn-primary" @click="openDemoUrl(openUrl)">
          <UIcon name="i-lucide-external-link" class="h-4 w-4" />
          Ouvrir le site
        </button>
        <NuxtLink v-if="site" :to="`/dashboard/demo-sites/${site.id}/edit`" class="app-btn-secondary">
          <UIcon name="i-lucide-square-pen" class="h-4 w-4" />
          Modifier les infos
        </NuxtLink>
      </div>
    </div>

    <UiLoader v-if="pending" />

    <UiCallout v-else-if="loadError" variant="danger">{{ loadError }}</UiCallout>

    <template v-else-if="site">
      <header class="space-y-2">
        <p class="text-xs font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Site démo</p>
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="app-page-title">{{ site.business_name }}</h1>
          <span :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', statusClass]">
            {{ statusLabel }}
          </span>
        </div>
        <p class="text-sm text-[var(--app-ink-soft)]">{{ site.slug }} · {{ templateLabel }}</p>
      </header>

      <UiCallout v-if="site.verification_message && !DemoSiteService.isDemoSiteReachable(site)" variant="warning">
        {{ site.verification_message }}
      </UiCallout>
      <UiCallout v-if="site.local_demo_url && site.local_demo_url !== site.demo_url" variant="success">
        URL locale : {{ site.local_demo_url }}
      </UiCallout>

      <div class="grid gap-4 @sm:grid-cols-2 @4xl:grid-cols-4">
        <div v-for="stat in stats" :key="stat.label" class="app-card p-4">
          <p class="app-label">{{ stat.label }}</p>
          <p
            class="mt-1 text-xl font-semibold text-[var(--app-ink)]"
            :class="[
              stat.tone === 'success' && 'text-[var(--app-green)]',
              stat.tone === 'warning' && 'text-[var(--app-accent-ink)]',
              stat.tone === 'muted' && 'truncate text-base',
            ]"
          >
            {{ stat.value }}
          </p>
        </div>
      </div>

      <section class="app-card space-y-5 p-5 md:p-6">
        <div>
          <h2 class="text-base font-semibold text-[var(--app-ink)]">Aperçu & template</h2>
          <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
            L'aperçu montre le site publié. Choisissez un autre modèle ou d'autres couleurs pour voir le rendu, puis
            régénérez pour l'appliquer au site du prospect.
          </p>
        </div>

        <UiLoader v-if="loadingTemplates" />
        <DemoSitesTemplatePicker
          v-else-if="templates.length"
          v-model="selectedTemplateId"
          :templates="templates"
          :theme="selectedTheme"
          :published-site-url="publishedSiteUrl"
          @update:theme="selectedTheme = $event"
        />

        <div
          v-if="hasPendingTemplateChanges"
          class="flex flex-col gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] px-4 py-3.5 @2xl:flex-row @2xl:items-center @2xl:justify-between"
        >
          <p class="flex items-start gap-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
            <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Ces changements ne sont pas encore en ligne : régénérez pour publier le nouveau rendu.
          </p>
          <div class="flex shrink-0 gap-2">
            <button
              type="button"
              class="app-btn-secondary h-8 min-h-8 px-3 text-xs"
              :disabled="applyingTemplate"
              @click="resetTemplateChanges"
            >
              Annuler
            </button>
            <button
              type="button"
              class="app-btn-primary h-8 min-h-8 px-3 text-xs"
              :disabled="applyingTemplate"
              @click="applyTemplateChanges"
            >
              {{ applyingTemplate ? 'Régénération…' : 'Appliquer & régénérer' }}
            </button>
          </div>
        </div>
      </section>

      <div class="grid items-start gap-5 @2xl:grid-cols-2 @5xl:grid-cols-3">
        <div class="app-card space-y-4 p-5">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Résumé</h2>
          <dl class="space-y-3 text-xs">
            <div class="flex justify-between gap-3">
              <dt class="text-[var(--app-ink-soft)]">Template</dt>
              <dd class="text-right text-[var(--app-ink)]">{{ templateLabel }}</dd>
            </div>
            <div v-if="site.city" class="flex justify-between gap-3">
              <dt class="text-[var(--app-ink-soft)]">Ville</dt>
              <dd class="text-right text-[var(--app-ink)]">{{ site.city }}</dd>
            </div>
            <div v-if="site.email" class="flex justify-between gap-3">
              <dt class="text-[var(--app-ink-soft)]">Email client</dt>
              <dd class="text-right break-all text-[var(--app-ink)]">{{ site.email }}</dd>
            </div>
            <div v-if="site.phone" class="flex justify-between gap-3">
              <dt class="text-[var(--app-ink-soft)]">Téléphone</dt>
              <dd class="text-right text-[var(--app-ink)]">{{ site.phone }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-[var(--app-ink-soft)]">Expire dans</dt>
              <dd class="text-right text-[var(--app-ink)]">{{ daysLeft }} jours</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-[var(--app-ink-soft)]">Créé le</dt>
              <dd class="text-right text-[var(--app-ink)]">{{ formatNumericDate(site.created_at) }}</dd>
            </div>
          </dl>
          <div v-if="site.description" class="border-t border-[var(--app-line)] pt-4">
            <h3 class="text-xs font-semibold text-[var(--app-ink)]">Description</h3>
            <p class="mt-2 text-xs leading-relaxed whitespace-pre-wrap text-[var(--app-ink-soft)]">
              {{ site.description }}
            </p>
          </div>
        </div>

        <div class="app-card space-y-3 p-5">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Vidéo de prospection</h2>
            <span
              v-if="videoStatusLabel"
              :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', videoStatusClass]"
            >
              {{ videoStatusLabel }}
            </span>
          </div>
          <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
            Votre webcam + le site du prospect qui défile, avec « Bonjour {Prénom} » à l'écran. La vignette est
            utilisable dans les emails via {vignette_video}.
          </p>

          <div v-if="isVideoGenerating" class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
            <UIcon name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            Génération en cours (capture + montage)…
          </div>

          <UiCallout v-else-if="site.video_status === 'failed'" variant="danger">
            <span class="block max-h-32 overflow-y-auto break-words">
              {{ site.video_error || 'La génération a échoué.' }}
            </span>
          </UiCallout>

          <template v-if="site.video_status === 'ready' && site.video_page_url">
            <button
              type="button"
              class="block w-full cursor-pointer overflow-hidden rounded-lg border border-[var(--app-line)] transition-opacity hover:opacity-90"
              title="Ouvrir la page vidéo"
              @click="openVideoPage(site.video_page_url)"
            >
              <img
                v-if="site.video_thumbnail_url"
                :src="site.video_thumbnail_url"
                alt="Vignette de la vidéo de prospection"
                class="w-full"
              />
            </button>
            <div class="space-y-2">
              <button type="button" class="app-btn-secondary w-full text-xs" @click="copyDemoUrl(site.video_page_url)">
                {{ copied ? 'Lien copié !' : 'Copier le lien vidéo' }}
              </button>
              <button
                type="button"
                class="app-btn-secondary w-full text-xs"
                :disabled="generatingVideo"
                @click="handleGenerateVideo"
              >
                {{ generatingVideo ? 'Lancement…' : 'Régénérer la vidéo' }}
              </button>
              <button
                type="button"
                class="app-btn-secondary w-full text-xs text-[var(--app-red)]"
                :disabled="deletingVideo"
                @click="askDeleteVideo"
              >
                {{ deletingVideo ? 'Suppression…' : 'Supprimer la vidéo' }}
              </button>
            </div>
          </template>

          <button
            v-if="!isVideoGenerating && site.video_status !== 'ready'"
            type="button"
            class="app-btn-primary w-full text-xs"
            :disabled="generatingVideo"
            @click="handleGenerateVideo"
          >
            <UIcon name="i-lucide-clapperboard" class="h-3.5 w-3.5" />
            {{ generatingVideo ? 'Lancement…' : site.video_status === 'failed' ? 'Réessayer' : 'Générer la vidéo' }}
          </button>

          <NuxtLink
            to="/dashboard/settings/video"
            class="block text-center text-[11px] text-[var(--app-ink-soft)] underline underline-offset-2 transition-colors hover:text-[var(--app-ink)]"
          >
            Configurer mon clip webcam (Paramètres
            <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Vidéo de prospection)
          </NuxtLink>
        </div>

        <div class="space-y-5">
          <div class="app-card space-y-2 p-5">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Actions</h2>
            <button v-if="openUrl" type="button" class="app-btn-secondary w-full text-xs" @click="copyDemoUrl(openUrl)">
              {{ copied ? 'Lien copié !' : 'Copier le lien' }}
            </button>
            <button
              type="button"
              class="app-btn-secondary w-full text-xs"
              :disabled="regenerating"
              @click="handleRegenerate"
            >
              {{ regenerating ? 'Régénération…' : 'Régénérer le contenu' }}
            </button>
            <button type="button" class="app-btn-secondary w-full text-xs" :disabled="verifying" @click="handleVerify">
              {{ verifying ? 'Vérification…' : "Revérifier l'URL" }}
            </button>
            <button type="button" class="app-btn-secondary w-full text-xs" :disabled="exporting" @click="handleExport">
              <UIcon name="i-lucide-download" class="h-3.5 w-3.5" />
              {{ exporting ? 'Préparation du zip…' : 'Exporter le code' }}
            </button>
            <button
              type="button"
              class="app-btn-secondary w-full text-xs text-[var(--app-red)]"
              :disabled="deleting"
              @click="askDeleteSite"
            >
              {{ deleting ? 'Suppression…' : 'Supprimer le site' }}
            </button>
          </div>

          <div v-if="site.storyblok_editor_url" class="app-card space-y-2 p-5">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Storyblok CMS</h2>
            <p v-if="site.storyblok_invite_sent" class="text-xs text-[var(--app-green)]">
              Invitation envoyée à {{ site.storyblok_login_email || site.email }}
            </p>
            <button
              type="button"
              class="app-btn-secondary w-full text-xs"
              @click="openDemoUrl(site.storyblok_editor_url)"
            >
              Ouvrir l'éditeur
            </button>
            <button
              v-if="!site.storyblok_invite_sent"
              type="button"
              class="app-btn-secondary w-full text-xs"
              :disabled="inviting"
              @click="handleInvite"
            >
              {{ inviting ? 'Envoi…' : 'Inviter le client au CMS' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <UiConfirmModal
      ref="deleteVideoModalRef"
      title="Supprimer la vidéo"
      message="Supprimer la vidéo de prospection de ce site ? Le lien envoyé dans les emails ne fonctionnera plus."
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDeleteVideoConfirmed"
    />

    <UiConfirmModal
      ref="deleteSiteModalRef"
      title="Supprimer le site démo"
      :message="deleteSiteMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDeleteConfirmed"
    />
  </div>
</template>

<script lang="ts" setup>
import { formatNumericDate } from '~/utils/date'
import type { UseCopyToClipboardReturn, UseOpenExternalUrlReturn, UseToastReturn } from '~/types/Composables'
import type { DemoSiteStat } from '~/types/DemoSiteDetailPage'
import type { ComputedRef, Ref } from 'vue'
import type { DemoSite, DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'
import { DEFAULT_DEMO_SITE_THEME, DemoSiteService } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route: ReturnType<typeof useRoute> = useRoute()
const demoSiteId: number = Number(route.params.id)
const { copy, copied }: UseCopyToClipboardReturn = useCopyToClipboard()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()
const toast: UseToastReturn = useToast()

const site: Ref<DemoSite | null> = ref(null)
const pending: Ref<boolean> = ref(true)
const loadError: Ref<string | null> = ref(null)
const templates: Ref<DemoSiteTemplate[]> = ref([])
const loadingTemplates: Ref<boolean> = ref(true)
const selectedTemplateId: Ref<string> = ref('')
const selectedTheme: Ref<DemoSiteTheme> = ref({ ...DEFAULT_DEMO_SITE_THEME })
const applyingTemplate: Ref<boolean> = ref(false)
const verifying: Ref<boolean> = ref(false)
const regenerating: Ref<boolean> = ref(false)
const deleting: Ref<boolean> = ref(false)
const inviting: Ref<boolean> = ref(false)
const exporting: Ref<boolean> = ref(false)
const generatingVideo: Ref<boolean> = ref(false)
const deletingVideo: Ref<boolean> = ref(false)
const deleteVideoModalRef: Ref<{ open: () => void } | null> = ref(null)
const deleteSiteModalRef: Ref<{ open: () => void } | null> = ref(null)
let videoPollTimer: ReturnType<typeof setInterval> | null = null

const templateLabel: ComputedRef<string> = computed((): string => {
  const templateId: string = site.value?.template_id ?? ''
  return templates.value.find((template: DemoSiteTemplate): boolean => template.id === templateId)?.name ?? templateId
})

const openUrl: ComputedRef<string | null> = computed((): string | null =>
  site.value ? DemoSiteService.getDemoSiteOpenUrl(site.value) : null,
)

const statusLabel: ComputedRef<string> = computed((): string => {
  if (!site.value) return ''
  if (DemoSiteService.isDemoSiteReachable(site.value)) return 'En ligne'
  if (site.value.status === 'failed') return 'Échec'
  if (site.value.status === 'unavailable') return 'Hors ligne'
  return site.value.status
})

const statusClass: ComputedRef<string> = computed((): string => {
  if (site.value && DemoSiteService.isDemoSiteReachable(site.value))
    return 'bg-[var(--app-green-soft)] text-[var(--app-green)]'
  if (site.value?.status === 'failed') return 'bg-[var(--app-red-soft)] text-[var(--app-red)]'
  return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
})

const daysLeft: ComputedRef<number> = computed((): number =>
  site.value ? DemoSiteService.daysUntilExpiry(site.value.expires_at) : 0,
)

const deleteSiteMessage: ComputedRef<string> = computed(
  (): string => `Supprimer « ${site.value?.business_name ?? ''} » ? Le site en ligne et son lien seront perdus.`,
)

const hasPendingTemplateChanges: ComputedRef<boolean> = computed((): boolean => {
  if (!site.value || !selectedTemplateId.value) return false
  if (selectedTemplateId.value !== site.value.template_id) return true
  const publishedTheme: DemoSiteTheme = site.value.theme ?? DEFAULT_DEMO_SITE_THEME
  return (['primary', 'secondary', 'accent'] as const).some(
    (key: keyof DemoSiteTheme): boolean => publishedTheme[key] !== selectedTheme.value[key],
  )
})

/** Real published site shown in the preview — dropped while changes are pending. */
const publishedSiteUrl: ComputedRef<string | null> = computed((): string | null =>
  hasPendingTemplateChanges.value ? null : openUrl.value,
)

const isVideoGenerating: ComputedRef<boolean> = computed(
  (): boolean => site.value?.video_status === 'pending' || site.value?.video_status === 'generating',
)

const videoStatusLabel: ComputedRef<string | null> = computed((): string | null => {
  switch (site.value?.video_status) {
    case 'pending':
    case 'generating':
      return 'En cours'
    case 'ready':
      return 'Prête'
    case 'failed':
      return 'Échec'
    default:
      return null
  }
})

const videoStatusClass: ComputedRef<string> = computed((): string => {
  if (site.value?.video_status === 'ready') return 'bg-[var(--app-green-soft)] text-[var(--app-green)]'
  if (site.value?.video_status === 'failed') return 'bg-[var(--app-red-soft)] text-[var(--app-red)]'
  return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
})

const stats: ComputedRef<DemoSiteStat[]> = computed((): DemoSiteStat[] => {
  if (!site.value) return []
  const urlLive: boolean = DemoSiteService.isDemoSiteReachable(site.value)
  return [
    {
      label: 'Statut URL',
      value: urlLive ? 'Live' : 'Offline',
      tone: urlLive ? 'success' : 'warning',
    },
    {
      label: 'Jours restants',
      value: String(daysLeft.value),
      tone: undefined,
    },
    {
      label: 'CMS',
      value: site.value.storyblok_invite_sent ? 'Invité' : 'Non invité',
      tone: site.value.storyblok_invite_sent ? 'success' : undefined,
    },
    {
      label: 'Slug',
      value: site.value.slug,
      tone: 'muted',
    },
  ]
})

/**
 * Point the picker back at the template and colors currently published.
 */
function resetTemplateChanges(): void {
  if (!site.value) return
  selectedTemplateId.value = site.value.template_id
  selectedTheme.value = { ...(site.value.theme ?? DEFAULT_DEMO_SITE_THEME) }
}

/**
 * Persist the picked template and colors, which regenerates the published site.
 * @returns A promise resolved once the site has been regenerated.
 */
async function applyTemplateChanges(): Promise<void> {
  applyingTemplate.value = true
  try {
    site.value = await DemoSiteService.updateDemoSite(demoSiteId, {
      template_id: selectedTemplateId.value,
      theme: { ...selectedTheme.value },
    })
    resetTemplateChanges()
    toast.success('Site régénéré avec le nouveau modèle')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la mise à jour du modèle')
  } finally {
    applyingTemplate.value = false
  }
}

/**
 * Open the live demo URL in a new browser tab.
 * @param url - URL to open outside the app.
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Copy the live demo URL to the clipboard.
 * @param url - URL to copy.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

/**
 * Verify that the deployed demo site is reachable.
 */
async function handleVerify(): Promise<void> {
  verifying.value = true
  try {
    site.value = await DemoSiteService.verifyDemoSite(demoSiteId)
  } finally {
    verifying.value = false
  }
}

/**
 * Regenerate the demo site content from the fields already stored.
 */
async function handleRegenerate(): Promise<void> {
  regenerating.value = true
  try {
    site.value = await DemoSiteService.regenerateDemoSite(demoSiteId)
    toast.success('Contenu régénéré')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la régénération')
  } finally {
    regenerating.value = false
  }
}

/**
 * Invite the client to the Storyblok CMS workspace.
 */
async function handleInvite(): Promise<void> {
  inviting.value = true
  try {
    site.value = await DemoSiteService.inviteDemoSiteClientToCms(demoSiteId)
    toast.success('Invitation envoyée au client')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Échec de l'invitation")
  } finally {
    inviting.value = false
  }
}

/**
 * Export the demo site source code as a downloadable archive.
 */
async function handleExport(): Promise<void> {
  if (!site.value) return
  exporting.value = true
  try {
    await DemoSiteService.exportDemoSiteCode(demoSiteId, site.value.slug)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Échec de l'export du code")
  } finally {
    exporting.value = false
  }
}

/**
 * Open the delete-site confirmation modal.
 */
function askDeleteSite(): void {
  deleteSiteModalRef.value?.open()
}

/**
 * Delete the demo site once confirmed, then go back to the list.
 */
async function handleDeleteConfirmed(): Promise<void> {
  deleting.value = true
  try {
    await DemoSiteService.deleteDemoSite(demoSiteId)
    await navigateTo('/dashboard/demo-sites')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la suppression')
  } finally {
    deleting.value = false
  }
}

/**
 * Stop the video-status polling loop.
 */
function stopVideoPolling(): void {
  if (videoPollTimer !== null) {
    clearInterval(videoPollTimer)
    videoPollTimer = null
  }
}

/**
 * Poll the site every 5 s while the video is generating (background job).
 */
function startVideoPolling(): void {
  if (videoPollTimer !== null) return
  videoPollTimer = setInterval(async (): Promise<void> => {
    try {
      site.value = await DemoSiteService.getDemoSite(demoSiteId)
    } catch {
      // Erreur transitoire : on retentera au prochain tick.
    }
    if (!isVideoGenerating.value) stopVideoPolling()
  }, 5000)
}

/**
 * Start (or restart) the prospection-video generation.
 */
async function handleGenerateVideo(): Promise<void> {
  generatingVideo.value = true
  try {
    site.value = await DemoSiteService.generateDemoSiteVideo(demoSiteId)
    startVideoPolling()
    toast.success('Génération de la vidéo lancée (capture + montage en tâche de fond)')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec du lancement de la génération')
  } finally {
    generatingVideo.value = false
  }
}

/**
 * Open the delete-video confirmation modal.
 */
function askDeleteVideo(): void {
  deleteVideoModalRef.value?.open()
}

/**
 * Delete the generated video once confirmed in the modal.
 */
async function handleDeleteVideoConfirmed(): Promise<void> {
  deletingVideo.value = true
  try {
    site.value = await DemoSiteService.deleteDemoSiteVideo(demoSiteId)
    toast.success('Vidéo supprimée')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la suppression de la vidéo')
  } finally {
    deletingVideo.value = false
  }
}

/**
 * Open the tracked player page with the in-app marker (adds a close button).
 * @param url - Player page URL of the site's prospection video.
 */
async function openVideoPage(url: string): Promise<void> {
  await openExternalUrl(`${url}${url.includes('?') ? '&' : '?'}from=app`)
}

onMounted(async (): Promise<void> => {
  try {
    site.value = await DemoSiteService.getDemoSite(demoSiteId)
    resetTemplateChanges()
    if (isVideoGenerating.value) startVideoPolling()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger le site'
  } finally {
    pending.value = false
  }
  try {
    templates.value = await DemoSiteService.listDemoSiteTemplates()
  } catch {
    // Sans le catalogue, la fiche reste lisible : seul le bloc de sélection disparaît.
  } finally {
    loadingTemplates.value = false
  }
})

onBeforeUnmount((): void => {
  stopVideoPolling()
})
</script>
