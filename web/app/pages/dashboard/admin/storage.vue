<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
      <div class="min-w-0">
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Administration
        </p>
        <h1 class="app-page-title mt-2">Stockage</h1>
        <p class="mt-1.5 max-w-2xl text-sm text-[var(--app-ink-soft)]">
          <template v-if="listing">
            {{ listing.total }} fichier{{ listing.total > 1 ? 's' : '' }} · {{ formatSize(listing.total_size) }} ·
            <span class="text-[var(--app-ink)]">{{ listing.bucket }}</span>
          </template>
          <template v-else>Fichiers hébergés sur Cloudflare R2.</template>
        </p>
      </div>
      <button
        type="button"
        class="app-btn-secondary h-9 shrink-0 self-start px-4 text-xs whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="isLoading"
        @click="load"
      >
        <UIcon name="i-lucide-refresh-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
        Actualiser
      </button>
    </div>

    <UiCallout v-if="error" variant="danger">{{ error }}</UiCallout>

    <div
      v-if="expiredCount > 0"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--app-red)]/30 bg-[var(--app-red-soft)] px-4 py-3.5"
    >
      <div class="flex min-w-0 items-start gap-3">
        <UIcon name="i-lucide-circle-alert" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-red)]" />
        <div class="min-w-0">
          <p class="text-sm font-semibold text-[var(--app-ink)]">
            {{ expiredCount }} fichier{{ expiredCount > 1 ? 's' : '' }} au-delà de {{ TTL_DAYS }} jours
          </p>
          <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
            Le nettoyage automatique aurait dû les supprimer.
          </p>
        </div>
      </div>
      <button type="button" class="app-btn-danger h-9 shrink-0 px-4 text-xs" :disabled="isActing" @click="askPurge">
        Purger
      </button>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="filter in FILTERS"
        :key="filter.prefix"
        type="button"
        :class="[
          'cursor-pointer rounded-full border px-3 py-1 text-xs transition-colors',
          activePrefix === filter.prefix
            ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
            : 'border-[var(--app-line)] text-[var(--app-ink)] hover:bg-[var(--app-surface-2)]',
        ]"
        @click="applyFilter(filter.prefix)"
      >
        {{ filter.label }}
      </button>
    </div>

    <UiLoader v-if="isLoading" label="Lecture du bucket…" />

    <div v-else-if="listing && listing.items.length" class="space-y-2">
      <div class="flex flex-wrap items-center justify-between gap-2 px-1">
        <label class="flex cursor-pointer items-center gap-2 text-xs text-[var(--app-ink-soft)]">
          <input
            type="checkbox"
            class="h-4 w-4 cursor-pointer accent-[var(--app-ink)]"
            :checked="allSelected"
            @change="toggleSelectAll"
          />
          Tout sélectionner
        </label>
        <button
          v-if="isProspectPhotosView"
          type="button"
          class="app-btn-secondary h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="isActing"
          title="Supprimer les photos que plus aucun prospect ne référence"
          @click="askPurgeOrphans"
        >
          <UIcon name="i-lucide-recycle" class="h-3.5 w-3.5" />
          Purger les orphelines
        </button>
      </div>

      <div
        v-for="item in listing.items"
        :key="item.key"
        class="app-card overflow-hidden p-0"
        :class="isSelected(item.key) && 'ring-1 ring-[var(--app-ink)]'"
      >
        <div class="flex items-center gap-3 px-4 py-3">
          <input
            type="checkbox"
            class="h-4 w-4 shrink-0 cursor-pointer accent-[var(--app-ink)]"
            :checked="isSelected(item.key)"
            :aria-label="`Sélectionner ${displayName(item)}`"
            @change="toggleSelect(item.key)"
          />
          <button
            type="button"
            class="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-left"
            :aria-expanded="openKey === item.key"
            @click="togglePreview(item)"
          >
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
              <UIcon :name="kindIcon(item.kind)" class="h-4 w-4 text-[var(--app-ink-soft)]" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-[var(--app-ink)]">{{ displayName(item) }}</span>
              <span class="block truncate text-xs text-[var(--app-ink-soft)]">
                {{ kindLabel(item.kind) }} · {{ formatSize(item.size) }} ·
                {{ formatShortMonthDate(item.last_modified) }}
                <template v-if="item.is_expired"> · <span class="text-[var(--app-red)]">expiré</span></template>
                <template v-else-if="item.expires_in_days !== null">
                  · expire dans {{ item.expires_in_days }} j
                </template>
              </span>
            </span>
          </button>

          <div class="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              class="app-btn-secondary h-8 px-2.5 text-xs"
              title="Copier le lien"
              @click="copyLink(item.url)"
            >
              <UIcon name="i-lucide-link" class="h-3.5 w-3.5" />
            </button>
            <button type="button" class="app-btn-danger h-8 px-2.5 text-xs" title="Supprimer" @click="askDelete(item)">
              <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div
          class="grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none"
          :class="openKey === item.key ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
        >
          <div class="overflow-hidden">
            <div class="space-y-3 border-t border-[var(--app-line)] px-4 py-4">
              <video
                v-if="openKey === item.key && isVideo(item)"
                :src="item.url"
                controls
                playsinline
                preload="metadata"
                class="aspect-video w-full max-w-lg rounded-lg border border-[var(--app-line)] bg-black"
              />
              <img
                v-else-if="openKey === item.key && isImage(item)"
                :src="item.url"
                :alt="displayName(item)"
                class="max-h-64 rounded-lg border border-[var(--app-line)]"
              />
              <p class="font-mono text-xs break-all text-[var(--app-ink-soft)]">{{ item.key }}</p>
              <a
                :href="item.url"
                target="_blank"
                rel="noopener"
                class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
              >
                <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                Ouvrir dans un onglet
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <UiEmptyState
      v-else-if="listing"
      title="Aucun fichier"
      :description="
        activePrefix ? 'Rien dans ce filtre.' : 'Le bucket est vide — les vidéos générées apparaîtront ici.'
      "
    />

    <UiCollapsibleCard icon="i-lucide-stethoscope" title="Cohérence avec la base" :suffix="healthSuffix">
      <div class="space-y-4 px-4 py-4">
        <p v-if="!hasHealthIssues" class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
          Chaque vidéo marquée « prête » a bien son fichier, et rien ne traîne au-delà de {{ TTL_DAYS }} jours.
        </p>
        <div v-for="group in healthGroups" v-else :key="group.label">
          <template v-if="group.keys.length">
            <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
              {{ group.label }} ({{ group.keys.length }})
            </p>
            <p class="mt-0.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">{{ group.hint }}</p>
            <ul class="mt-1.5 space-y-1">
              <li v-for="key in group.keys.slice(0, 5)" :key="key" class="truncate font-mono text-xs">{{ key }}</li>
              <li v-if="group.keys.length > 5" class="text-xs text-[var(--app-ink-soft)]">
                + {{ group.keys.length - 5 }} autre(s)
              </li>
            </ul>
          </template>
        </div>
      </div>
    </UiCollapsibleCard>

    <Transition name="bulkbar">
      <div v-if="selectedKeys.length > 0" class="fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
        <div
          class="app-card flex flex-wrap items-center justify-center gap-2 rounded-full px-4 py-2.5 shadow-[var(--app-shadow-soft)] backdrop-blur"
        >
          <span class="font-label px-1.5 text-xs font-medium text-[var(--app-ink)]">
            {{ selectedKeys.length }} sélectionné{{ selectedKeys.length > 1 ? 's' : '' }}
          </span>
          <span class="hidden h-5 w-px bg-[var(--app-line)] sm:block"></span>
          <button
            type="button"
            class="app-btn-danger h-9 px-4 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isActing"
            @click="askBulkDelete"
          >
            <UIcon
              :name="isActing ? 'i-lucide-loader-circle' : 'i-lucide-trash-2'"
              :class="['h-3.5 w-3.5', isActing && 'animate-spin']"
            />
            Supprimer
          </button>
          <button
            type="button"
            class="ml-0.5 cursor-pointer rounded-full p-2 text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Désélectionner tout"
            @click="clearSelection"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </Transition>

    <UiConfirmModal
      ref="confirmModal"
      :title="confirmTitle"
      :message="confirmMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="runConfirmed"
    />
  </div>
</template>

<script lang="ts" setup>
import { formatShortMonthDate } from '~/utils/date'
import type { UseToastReturn } from '~/types/Composables'
import type { PendingStorageAction } from '~/types/StoragePage'
import type { ComputedRef, Ref } from 'vue'
import type {
  StorageActionResponse,
  StorageHealthResponse,
  StorageListResponse,
  StorageObject,
} from '~/services/adminStorageService'
import { computed, onMounted, ref } from 'vue'
import { AdminStorageService } from '~/services/adminStorageService'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'admin'] })

/** Demo deliverables TTL, mirrored from the API. */
const TTL_DAYS: number = 14

/** Key prefix of the rehosted prospect photos (the only category with an orphan-purge action). */
const PROSPECT_PHOTOS_PREFIX: string = 'images/prospects/'

/** Prefix filters shown as pills. */
const FILTERS: Array<{ label: string; prefix: string }> = [
  { label: 'Tout', prefix: '' },
  { label: 'Vidéos', prefix: 'videos/websites/' },
  { label: 'Vignettes', prefix: 'images/websites/' },
  { label: 'Clips webcam', prefix: 'videos/presenter/' },
  { label: 'Photos prospects', prefix: PROSPECT_PHOTOS_PREFIX },
  { label: 'Support', prefix: 'images/support/' },
]

/** Icon per object category. */
const KIND_ICONS: Record<string, string> = {
  website_video: 'i-lucide-video',
  website_thumbnail: 'i-lucide-image',
  presenter: 'i-lucide-webcam',
  support: 'i-lucide-paperclip',
  prospect_photo: 'i-lucide-image',
  other: 'i-lucide-file',
}

/** Human label per object category — distinguishes a prospect's video from its thumbnail. */
const KIND_LABELS: Record<string, string> = {
  website_video: 'Vidéo',
  website_thumbnail: 'Vignette',
  presenter: 'Clip webcam',
  support: 'Pièce jointe',
  prospect_photo: 'Photo prospect',
  other: 'Fichier',
}

const toast: UseToastReturn = useToast()

const listing: Ref<StorageListResponse | null> = ref(null)
const health: Ref<StorageHealthResponse | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const isActing: Ref<boolean> = ref(false)
const error: Ref<string> = ref('')
const activePrefix: Ref<string> = ref('')
const openKey: Ref<string | null> = ref(null)
const pendingKey: Ref<string | null> = ref(null)
const pendingAction: Ref<PendingStorageAction | null> = ref(null)
const selectedKeys: Ref<string[]> = ref([])
const confirmTitle: Ref<string> = ref('')
const confirmMessage: Ref<string> = ref('')
const confirmModal: Ref<{ open: () => void } | null> = ref(null)

/** Number of objects past their TTL in the current listing. */
const expiredCount: ComputedRef<number> = computed(
  (): number => listing.value?.items.filter((item: StorageObject): boolean => item.is_expired).length ?? 0,
)

/** Keys currently listed — the pool that « tout sélectionner » operates on. */
const visibleKeys: ComputedRef<string[]> = computed(
  (): string[] => listing.value?.items.map((item: StorageObject): string => item.key) ?? [],
)

/** Whether every listed object is currently selected. */
const allSelected: ComputedRef<boolean> = computed(
  (): boolean =>
    visibleKeys.value.length > 0 && visibleKeys.value.every((key: string): boolean => selectedKeys.value.includes(key)),
)

/** Whether the active filter is the rehosted prospect photos (the only category with an orphan purge). */
const isProspectPhotosView: ComputedRef<boolean> = computed(
  (): boolean => activePrefix.value === PROSPECT_PHOTOS_PREFIX,
)

/** Consistency groups, each with a plain-French explanation. */
const healthGroups: ComputedRef<Array<{ label: string; hint: string; keys: string[] }>> = computed(
  (): Array<{ label: string; hint: string; keys: string[] }> => [
    {
      label: 'Orphelins',
      hint: 'Présents sur R2 mais plus rattachés à une démo.',
      keys: health.value?.orphan_objects ?? [],
    },
    {
      label: 'Fichiers manquants',
      hint: 'Démos marquées « prête » dont la vidéo a disparu.',
      keys: health.value?.missing_objects ?? [],
    },
    {
      label: `Au-delà de ${TTL_DAYS} jours`,
      hint: 'Auraient dû être purgés automatiquement.',
      keys: health.value?.expired_objects ?? [],
    },
  ],
)

/** Whether the consistency report found anything. */
const hasHealthIssues: ComputedRef<boolean> = computed((): boolean =>
  healthGroups.value.some((group: { keys: string[] }): boolean => group.keys.length > 0),
)

/** Short verdict shown next to the health card title. */
const healthSuffix: ComputedRef<string> = computed((): string => {
  if (!health.value) return ''
  const total: number = healthGroups.value.reduce(
    (sum: number, group: { keys: string[] }): number => sum + group.keys.length,
    0,
  )
  return total === 0 ? 'tout est cohérent' : `${total} à vérifier`
})

/**
 * Icon matching an object category.
 * @param kind - Raw category from the API.
 * @returns Lucide icon name.
 */
function kindIcon(kind: string): string {
  return KIND_ICONS[kind] ?? KIND_ICONS.other!
}

/**
 * Human label matching an object category.
 * @param kind - Raw category from the API.
 * @returns Localised label.
 */
function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? KIND_LABELS.other!
}

/**
 * Readable name for an object: the prospect when known, else the file name.
 * @param item - Storage object.
 * @returns Label shown as the row title.
 */
function displayName(item: StorageObject): string {
  if (item.prospect_name) return item.prospect_name
  if (item.slug) return item.slug
  return item.key.split('/').pop() || item.key
}

/**
 * Whether an object can be played inline.
 * @param item - Storage object.
 * @returns True for videos.
 */
function isVideo(item: StorageObject): boolean {
  return item.kind === 'website_video' || item.kind === 'presenter'
}

/**
 * Whether an object can be shown as an image.
 * @param item - Storage object.
 * @returns True for thumbnails, support attachments and rehosted prospect photos.
 */
function isImage(item: StorageObject): boolean {
  return item.kind === 'website_thumbnail' || item.kind === 'support' || item.kind === 'prospect_photo'
}

/**
 * Whether an object is in the multi-selection.
 * @param key - Object key.
 * @returns True when selected.
 */
function isSelected(key: string): boolean {
  return selectedKeys.value.includes(key)
}

/**
 * Toggle one object in the multi-selection.
 * @param key - Object key.
 */
function toggleSelect(key: string): void {
  selectedKeys.value = isSelected(key)
    ? selectedKeys.value.filter((selected: string): boolean => selected !== key)
    : [...selectedKeys.value, key]
}

/**
 * Select every listed object, or clear the selection when all are already selected.
 */
function toggleSelectAll(): void {
  selectedKeys.value = allSelected.value ? [] : [...visibleKeys.value]
}

/**
 * Clear the multi-selection.
 */
function clearSelection(): void {
  selectedKeys.value = []
}

/**
 * Format a byte count in a readable unit.
 * @param bytes - Raw size.
 * @returns Formatted label (e.g. « 12,4 Mo »).
 */
function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} Go`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${bytes} o`
}

/**
 * Load the listing and the consistency report.
 * @returns A promise resolving once both are loaded.
 */
async function load(): Promise<void> {
  isLoading.value = true
  error.value = ''
  try {
    listing.value = await AdminStorageService.getStorageObjects(activePrefix.value)
    // Drop from the selection any object that vanished (deleted elsewhere / filtered out).
    selectedKeys.value = selectedKeys.value.filter((key: string): boolean => visibleKeys.value.includes(key))
    health.value = await AdminStorageService.getStorageHealth().catch((): StorageHealthResponse | null => null)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Impossible de charger le stockage'
  } finally {
    isLoading.value = false
  }
}

/**
 * Apply a prefix filter and reload.
 * @param prefix - Key prefix to filter on.
 * @returns A promise resolving once reloaded.
 */
async function applyFilter(prefix: string): Promise<void> {
  activePrefix.value = prefix
  openKey.value = null
  clearSelection()
  await load()
}

/**
 * Toggle the inline preview of an object.
 * @param item - Object to preview.
 */
function togglePreview(item: StorageObject): void {
  openKey.value = openKey.value === item.key ? null : item.key
}

/**
 * Copy a public URL to the clipboard.
 * @param url - URL to copy.
 * @returns A promise resolving once copied.
 */
async function copyLink(url: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(url)
    toast.success('Lien copié')
  } catch {
    toast.error('Impossible de copier le lien')
  }
}

/**
 * Ask confirmation before deleting one object.
 * @param item - Object to delete.
 */
function askDelete(item: StorageObject): void {
  pendingAction.value = 'delete'
  pendingKey.value = item.key
  confirmTitle.value = 'Supprimer le fichier'
  confirmMessage.value = `Supprimer « ${displayName(item)} » ? Cette action est irréversible.`
  confirmModal.value?.open()
}

/**
 * Ask confirmation before deleting every selected object.
 */
function askBulkDelete(): void {
  pendingAction.value = 'bulk-delete'
  pendingKey.value = null
  confirmTitle.value = 'Supprimer les fichiers sélectionnés'
  confirmMessage.value = `Supprimer les ${selectedKeys.value.length} fichier(s) sélectionné(s) ? Cette action est irréversible.`
  confirmModal.value?.open()
}

/**
 * Ask confirmation before purging every expired object.
 */
function askPurge(): void {
  pendingAction.value = 'purge-expired'
  pendingKey.value = null
  confirmTitle.value = 'Purger les fichiers expirés'
  confirmMessage.value = `Supprimer les ${expiredCount.value} fichier(s) de plus de ${TTL_DAYS} jours ?`
  confirmModal.value?.open()
}

/**
 * Ask confirmation before purging prospect photos no enrichment references any more.
 */
function askPurgeOrphans(): void {
  pendingAction.value = 'purge-orphans'
  pendingKey.value = null
  confirmTitle.value = 'Purger les photos orphelines'
  confirmMessage.value = 'Supprimer les photos de prospect que plus aucun enrichissement ne référence ?'
  confirmModal.value?.open()
}

/**
 * Run the confirmed action, then reload.
 * @returns A promise resolving once the action completed.
 */
async function runConfirmed(): Promise<void> {
  isActing.value = true
  try {
    const result: StorageActionResponse = await runPendingAction()
    toast.success(result.message || 'Action effectuée')
    openKey.value = null
    await load()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    isActing.value = false
    pendingKey.value = null
    pendingAction.value = null
  }
}

/**
 * Dispatch the pending confirm action to its storage service call.
 * @returns The action result.
 */
function runPendingAction(): Promise<StorageActionResponse> {
  if (pendingAction.value === 'bulk-delete') {
    const keys: string[] = [...selectedKeys.value]
    clearSelection()
    return AdminStorageService.deleteStorageObjects(keys)
  }
  if (pendingAction.value === 'purge-orphans') return AdminStorageService.purgeOrphanProspectPhotos()
  if (pendingAction.value === 'purge-expired') return AdminStorageService.purgeExpiredStorage()
  return AdminStorageService.deleteStorageObject(pendingKey.value ?? '')
}

onMounted(async (): Promise<void> => {
  await load()
})
</script>

<style scoped>
.bulkbar-enter-active,
.bulkbar-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.bulkbar-enter-from,
.bulkbar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (prefers-reduced-motion: reduce) {
  .bulkbar-enter-active,
  .bulkbar-leave-active {
    transition: none;
  }
  .bulkbar-enter-from,
  .bulkbar-leave-to {
    transform: none;
  }
}
</style>
