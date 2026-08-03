<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
      <div class="min-w-0">
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Mes prospects</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">Tous vos prospects sauvegardés depuis vos recherches</p>
      </div>
      <div class="flex w-full flex-wrap items-center gap-2 sm:gap-3 @2xl:w-auto @2xl:justify-end">
        <NuxtLink
          to="/dashboard/search-prospects"
          class="app-btn-primary h-9 shrink-0 px-4 text-xs whitespace-nowrap @2xl:order-2"
        >
          <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
          Nouvelle recherche
        </NuxtLink>
        <div class="flex flex-wrap items-center gap-2 sm:gap-3 @2xl:order-1">
          <button
            :disabled="isLoading"
            class="app-btn-secondary h-9 shrink-0 px-4 text-xs whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
            @click="refreshProspects"
          >
            <UIcon name="i-lucide-refresh-cw" class="h-3.5 w-3.5" />
            Actualiser
          </button>
          <div class="relative shrink-0">
            <button
              type="button"
              class="app-btn-secondary h-9 px-4 text-xs whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isImporting"
              :aria-expanded="showImportMenu"
              @click.stop="showImportMenu = !showImportMenu"
            >
              <UIcon
                :name="isImporting ? 'i-lucide-loader-circle' : 'i-lucide-upload'"
                :class="['h-3.5 w-3.5', isImporting && 'animate-spin']"
              />
              {{ isImporting ? 'Import…' : 'Importer' }}
              <UIcon
                name="i-lucide-chevron-down"
                :class="['h-3 w-3 opacity-60 transition-transform', showImportMenu && 'rotate-180']"
              />
            </button>

            <div v-if="showImportMenu" class="fixed inset-0 z-40" @click="showImportMenu = false"></div>
            <div
              v-if="showImportMenu"
              class="absolute right-0 z-50 mt-1.5 w-56 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1 shadow-lg shadow-black/5"
            >
              <button
                type="button"
                class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                @click="handleImportClick"
              >
                <UIcon name="i-lucide-upload" class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
                Importer un fichier JSON
              </button>
              <button
                type="button"
                class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                @click="handleDownloadTemplate"
              >
                <UIcon name="i-lucide-file-json" class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
                Télécharger le modèle JSON
              </button>
            </div>
          </div>
          <input
            ref="importInput"
            type="file"
            accept=".json,application/json"
            class="hidden"
            @change="handleImportFile"
          />
          <button
            type="button"
            class="app-btn-secondary h-9 shrink-0 px-4 text-xs whitespace-nowrap"
            @click="openAddProspectDrawer"
          >
            <UIcon name="i-lucide-user-plus" class="h-3.5 w-3.5" />
            Ajouter manuellement
          </button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 @sm:grid-cols-2 @4xl:grid-cols-4">
      <UiStatCard label="Total Prospects" :value="totalProspects" icon="i-lucide-users" accent="neutral" />
      <UiStatCard label="Avec Email" :value="prospectsWithEmail" icon="i-lucide-mail" accent="emerald" />
      <UiStatCard label="Sans Site Web" :value="prospectsWithoutWebsite" icon="i-lucide-globe-lock" accent="danger" />
      <UiStatCard label="Avec Téléphone" :value="prospectsWithPhone" icon="i-lucide-phone" accent="sky" />
    </div>

    <div class="app-card space-y-3 p-4">
      <div class="flex justify-end">
        <div class="relative w-full @2xl:w-80">
          <UIcon
            name="i-lucide-search"
            class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
          />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Nom, ville, email..."
            aria-label="Rechercher un prospect"
            class="app-input pl-9"
          />
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 @sm:grid-cols-2 @4xl:grid-cols-4">
        <div>
          <label class="app-label mb-1.5 block">Site web</label>
          <UiSelectField v-model="filterWebsite" :options="websiteFilterOptions" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Ville</label>
          <UiCitySelect v-model="filterCity" placeholder="Toutes les villes" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Catégorie</label>
          <input v-model="filterCategory" type="text" placeholder="Ex: restaurant" class="app-input" />
        </div>
        <div class="flex items-end">
          <button class="app-btn-secondary w-full" @click="clearFilters">Réinitialiser</button>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-1 border-b border-[var(--app-line)]">
      <button
        type="button"
        class="relative cursor-pointer px-4 py-2.5 text-sm font-medium transition-colors"
        :class="
          activeTab === 'not_contacted'
            ? 'text-[var(--app-ink)]'
            : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
        "
        @click="activeTab = 'not_contacted'"
      >
        Pas contacté
        <span class="font-label ml-1.5 rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs">
          {{ notContactedCount }}
        </span>
        <span
          v-if="activeTab === 'not_contacted'"
          class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-[var(--app-accent)]"
        ></span>
      </button>
      <button
        type="button"
        class="relative cursor-pointer px-4 py-2.5 text-sm font-medium transition-colors"
        :class="
          activeTab === 'contacted' ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
        "
        @click="activeTab = 'contacted'"
      >
        Contacté
        <span class="font-label ml-1.5 rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs">
          {{ contactedCount }}
        </span>
        <span
          v-if="activeTab === 'contacted'"
          class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-[var(--app-accent)]"
        ></span>
      </button>

      <p v-if="hasNarrowingFilters" class="ml-auto flex items-center gap-2 pr-1 text-xs text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-filter" class="h-3 w-3" />
        {{ baseFiltered.length }} sur {{ totalProspects }} prospects
        <button
          type="button"
          class="cursor-pointer font-medium underline underline-offset-2 hover:text-[var(--app-ink)]"
          @click="clearFilters"
        >
          Tout afficher
        </button>
      </p>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-accent)]" />
    </div>

    <div v-else-if="error" class="app-card border-[var(--app-red)]/40 bg-[var(--app-red-soft)] p-5">
      <p class="font-semibold text-[var(--app-red)]">Erreur</p>
      <p class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ error }}</p>
    </div>

    <div v-else-if="filteredProspects.length === 0" class="app-card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucun prospect trouvé</h3>
      <p class="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-[var(--app-ink-soft)]">
        {{
          searchQuery || filterCity || filterCategory
            ? 'Essayez de modifier vos filtres pour élargir la sélection.'
            : 'Lancez une recherche pour trouver des artisans sans site web près de chez vous.'
        }}
      </p>
      <NuxtLink to="/dashboard/search-prospects" class="app-btn-primary mt-6 inline-flex">
        Trouver des prospects
      </NuxtLink>
    </div>

    <div v-else class="app-card overflow-hidden">
      <UiProspectTable
        :prospects="paginatedProspects"
        :selected-prospects="selectedProspects"
        @view-prospect="openDrawer"
        @edit-prospect="openProspectEditDrawer"
        @delete-prospect="handleDeleteProspect"
        @toggle-select="toggleSelect"
        @toggle-select-all="toggleSelectAll"
      />

      <div
        class="flex flex-col gap-3 border-t border-[var(--app-line)] bg-[var(--app-surface-2)]/50 px-4 py-3.5 sm:px-6 @2xl:flex-row @2xl:items-center @2xl:justify-between"
      >
        <div class="font-label text-xs text-[var(--app-ink-soft)]">
          {{ (currentPage - 1) * pageSize + 1 }}–{{ Math.min(currentPage * pageSize, filteredProspects.length) }} sur
          {{ filteredProspects.length }} prospects
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="currentPage === 1"
            class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage--"
          >
            Précédent
          </button>
          <span class="font-label px-2 text-xs text-[var(--app-ink-soft)]">
            Page {{ currentPage }} / {{ totalPages }}
          </span>
          <button
            :disabled="currentPage === totalPages"
            class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage++"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>

    <UiConfirmModal
      ref="deleteConfirmModal"
      title="Supprimer le prospect"
      :message="deleteConfirmMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="confirmDeleteProspect"
    />

    <UiConfirmModal
      ref="bulkDeleteConfirmModal"
      title="Supprimer les prospects sélectionnés"
      :message="bulkDeleteConfirmMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="confirmBulkDelete"
    />

    <Transition name="bulkbar">
      <div v-if="selectedProspects.length > 0" class="fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
        <div
          class="app-card flex flex-wrap items-center justify-center gap-2 rounded-full px-4 py-2.5 shadow-[var(--app-shadow-soft)] backdrop-blur"
        >
          <span class="font-label px-1.5 text-xs font-medium text-[var(--app-ink)]">
            {{ selectedProspects.length }} sélectionné{{ selectedProspects.length > 1 ? 's' : '' }}
          </span>
          <span class="hidden h-5 w-px bg-[var(--app-line)] sm:block"></span>
          <button type="button" class="app-btn-secondary h-9 px-4 text-xs" @click="exportSelected">
            <UIcon name="i-lucide-download" class="h-3.5 w-3.5" />Exporter
          </button>
          <button type="button" class="app-btn-secondary h-9 px-4 text-xs" @click="bulkCampaignOpen = true">
            <UIcon name="i-lucide-megaphone" class="h-3.5 w-3.5" />Campagne
          </button>
          <button
            type="button"
            class="app-btn-secondary h-9 px-4 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="bulkBusy"
            @click="bulkEnrich"
          >
            <UIcon
              :name="bulkBusy ? 'i-lucide-loader-circle' : 'i-lucide-sparkles'"
              :class="['h-3.5 w-3.5', bulkBusy && 'animate-spin']"
            />
            Enrichir
          </button>
          <button type="button" class="app-btn-primary h-9 px-4 text-xs" @click="bulkGenerateOpen = true">
            <UIcon name="i-lucide-globe" class="h-3.5 w-3.5" />Générer les sites
          </button>
          <button
            type="button"
            class="app-btn-danger h-9 px-4 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="bulkDeleting"
            @click="bulkDeleteConfirmModal?.open()"
          >
            <UIcon
              :name="bulkDeleting ? 'i-lucide-loader-circle' : 'i-lucide-trash-2'"
              :class="['h-3.5 w-3.5', bulkDeleting && 'animate-spin']"
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

    <UiBulkCampaignModal
      :open="bulkCampaignOpen"
      :prospect-ids="selectedIds"
      @close="bulkCampaignOpen = false"
      @added="handleBulkAdded"
    />

    <UiBulkGenerateModal
      :open="bulkGenerateOpen"
      :prospect-ids="selectedIds"
      @close="bulkGenerateOpen = false"
      @generated="handleBulkGenerated"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ProspectMutationNotice } from '~/types/DrawerStack'
import type { BulkEnrichResult } from '~/services/enrichmentService'
import type { LocationQueryValue } from 'vue-router'
import type { UseToastReturn } from '~/types/Composables'
import { ref, computed, watch, onMounted } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { Prospect, ProspectWebsiteFilter } from '~/types'
import { ProspectsService } from '~/services/prospectsService'
import { downloadProspectsJson, downloadProspectTemplateJson, parseProspectsJson } from '~/utils/prospectJson'
import { ProspectWebsite } from '~/utils/prospectWebsite'
import { EnrichmentService } from '~/services/enrichmentService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import type { BulkGenerateResult } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const prospects: Ref<Prospect[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)
const selectedProspects: Ref<string[]> = ref([])
const bulkCampaignOpen: Ref<boolean> = ref(false)
const bulkGenerateOpen: Ref<boolean> = ref(false)
const bulkBusy: Ref<boolean> = ref(false)
const searchQuery: Ref<string> = ref('')
const filterCategory: Ref<string> = ref('')
const filterCity: Ref<string> = ref('')
const filterWebsite: Ref<ProspectWebsiteFilter> = ref('no')
const activeTab: Ref<'not_contacted' | 'contacted'> = ref('not_contacted')

const websiteFilterOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Tous' },
  { value: 'yes', label: 'Oui' },
  { value: 'no', label: 'Non (aucun ou site mort)' },
  { value: 'dead', label: 'Site mort / annuaire' },
  { value: 'improvable', label: 'Améliorable (audit)' },
]
const currentPage: Ref<number> = ref(1)
const pageSize: number = 50

// Quick-delete (from table row icon)
const prospectToDelete: Ref<Prospect | null> = ref(null)
const deleteConfirmModal: Ref<{ open: () => void; close: () => void } | null> = ref(null)

// Bulk delete (from the selection bar)
const bulkDeleting: Ref<boolean> = ref(false)
const bulkDeleteConfirmModal: Ref<{ open: () => void; close: () => void } | null> = ref(null)

// Detail drawer
/** Persistent drawer stack (the prospect drawer is hosted by the layout). */
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const toast: UseToastReturn = useToast()

const deleteConfirmMessage: ComputedRef<string> = computed(() => {
  if (!prospectToDelete.value) return 'Cette action est irréversible.'
  return `Supprimer définitivement « ${prospectToDelete.value.name} » ? Cette action est irréversible.`
})

const bulkDeleteConfirmMessage: ComputedRef<string> = computed(() => {
  const count: number = selectedIds.value.length
  if (count === 1) return 'Supprimer définitivement ce prospect ? Il restera trouvable via une nouvelle recherche.'
  return `Supprimer définitivement ces ${count} prospects ? Ils resteront trouvables via une nouvelle recherche.`
})

const selectedIds: ComputedRef<number[]> = computed<number[]>(() =>
  selectedProspects.value.map((id: string) => Number(id)).filter((n: number) => !Number.isNaN(n)),
)

const totalProspects: ComputedRef<number> = computed(() => prospects.value.length)
const prospectsWithEmail: ComputedRef<number> = computed(
  () => prospects.value.filter((prospect: Prospect) => prospect.email).length,
)
const prospectsWithoutWebsite: ComputedRef<number> = computed(
  () => prospects.value.filter((prospect: Prospect) => !ProspectWebsite.hasWorkingWebsite(prospect)).length,
)
const prospectsWithPhone: ComputedRef<number> = computed(
  () => prospects.value.filter((prospect: Prospect) => prospect.phone).length,
)

/** Prospects matching every filter EXCEPT the contacted tab (drives the tab counts). */
const baseFiltered: ComputedRef<Prospect[]> = computed(() => {
  let filtered: Prospect[] = prospects.value

  if (searchQuery.value) {
    const query: string = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (prospect: Prospect) =>
        prospect.name.toLowerCase().includes(query) ||
        prospect.city?.toLowerCase().includes(query) ||
        prospect.email?.toLowerCase().includes(query) ||
        prospect.phone?.toLowerCase().includes(query),
    )
  }

  if (filterCity.value) {
    const city: string = filterCity.value.toLowerCase()
    filtered = filtered.filter((prospect: Prospect) => prospect.city?.toLowerCase().includes(city))
  }

  if (filterCategory.value) {
    const cat: string = filterCategory.value.toLowerCase()
    filtered = filtered.filter((prospect: Prospect) => prospect.category.toLowerCase().includes(cat))
  }

  if (filterWebsite.value === 'yes') {
    filtered = filtered.filter((prospect: Prospect) => ProspectWebsite.hasWorkingWebsite(prospect))
  } else if (filterWebsite.value === 'no') {
    // Un site mort ou un mini-site annuaire compte comme « sans site ».
    filtered = filtered.filter((prospect: Prospect) => !ProspectWebsite.hasWorkingWebsite(prospect))
  } else if (filterWebsite.value === 'dead') {
    // URL trouvée mais site mort ou mini-site annuaire → accroche « site hors ligne ».
    filtered = filtered.filter((prospect: Prospect) => ProspectWebsite.hasBrokenWebsite(prospect))
  } else if (filterWebsite.value === 'improvable') {
    // Site existant jugé faible par l'audit Lighthouse → cible refonte.
    filtered = filtered.filter(
      (prospect: Prospect) => !!prospect.website && prospect.lighthouse_json?.is_improvable === true,
    )
  }

  return filtered
})

/** Whether the filters hide part of the prospects — the tab counters only cover what is left. */
const hasNarrowingFilters: ComputedRef<boolean> = computed(
  (): boolean => baseFiltered.value.length !== prospects.value.length,
)

const notContactedCount: ComputedRef<number> = computed(
  () => baseFiltered.value.filter((prospect: Prospect) => !prospect.contacted).length,
)
const contactedCount: ComputedRef<number> = computed(
  () => baseFiltered.value.filter((prospect: Prospect) => prospect.contacted).length,
)

const filteredProspects: ComputedRef<Prospect[]> = computed(() =>
  baseFiltered.value.filter((prospect: Prospect) =>
    activeTab.value === 'contacted' ? prospect.contacted : !prospect.contacted,
  ),
)

const totalPages: ComputedRef<number> = computed(() => Math.ceil(filteredProspects.value.length / pageSize))

const paginatedProspects: ComputedRef<Prospect[]> = computed(() => {
  const start: number = (currentPage.value - 1) * pageSize
  return filteredProspects.value.slice(start, start + pageSize)
})

/**
 * Fetch prospects from the API.
 */
async function loadProspects(): Promise<void> {
  try {
    isLoading.value = true
    error.value = null
    prospects.value = await ProspectsService.listProspects()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du chargement des prospects'
  } finally {
    isLoading.value = false
  }
}

/**
 * Reload prospects and reset pagination.
 */
function refreshProspects(): void {
  currentPage.value = 1
  loadProspects()
}

/**
 * Reset all list filters to their defaults.
 */
function clearFilters(): void {
  searchQuery.value = ''
  filterCity.value = ''
  filterCategory.value = ''
  filterWebsite.value = 'no'
  currentPage.value = 1
}

// Reset to the first page whenever the active filter set or tab changes.
watch([activeTab, searchQuery, filterCity, filterCategory, filterWebsite], (): void => {
  currentPage.value = 1
})

/**
 * Toggle a single prospect in the selection.
 * @param prospect - The prospect whose checkbox was toggled.
 */
function toggleSelect(prospect: Prospect): void {
  const id: string = String(prospect.id)
  const index: number = selectedProspects.value.indexOf(id)
  if (index === -1) selectedProspects.value.push(id)
  else selectedProspects.value.splice(index, 1)
}

/**
 * Select or clear every prospect on the current page.
 * @param checked - True to add the page's prospects, false to remove them.
 */
function toggleSelectAll(checked: boolean): void {
  const pageIds: string[] = paginatedProspects.value.map((prospect: Prospect) => String(prospect.id))
  if (checked) {
    const set: Set<string> = new Set([...selectedProspects.value, ...pageIds])
    selectedProspects.value = Array.from(set)
  } else {
    const pageSet: Set<string> = new Set(pageIds)
    selectedProspects.value = selectedProspects.value.filter((id: string) => !pageSet.has(id))
  }
}

/** Clear the entire selection. */
function clearSelection(): void {
  selectedProspects.value = []
}

/**
 * Campaign modal succeeded — toast and clear the selection.
 * @param payload - The add-to-campaign result.
 * @param payload.campaignName - Name of the campaign the prospects were added to.
 * @param payload.count - Number of prospects added.
 */
function handleBulkAdded(payload: { campaignName: string; count: number }): void {
  toast.success(`${payload.count} prospect(s) ajouté(s) à « ${payload.campaignName} »`)
  clearSelection()
}

/**
 * Bulk generation finished — surface skipped/failed items and clear selection.
 * @param result - The aggregated bulk generation result.
 */
function handleBulkGenerated(result: BulkGenerateResult): void {
  if (result.failed > 0 || result.skipped_no_email.length > 0) {
    toast.info(
      `${result.created} site(s) créé(s) · ${result.skipped_no_email.length} sans email · ${result.failed} échec(s)`,
    )
  }
  clearSelection()
}

/**
 * Run enrichment for every selected prospect (sequential server-side).
 */
async function bulkEnrich(): Promise<void> {
  if (bulkBusy.value || selectedIds.value.length === 0) return
  bulkBusy.value = true
  try {
    const res: BulkEnrichResult = await EnrichmentService.runBulkEnrichment(selectedIds.value)
    toast.success(`Enrichissement : ${res.succeeded} réussi(s), ${res.failed} échec(s)`)
    clearSelection()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enrichissement")
  } finally {
    bulkBusy.value = false
  }
}

/** Open the detail drawer for a given prospect, browsable across the filtered list. */
function openDrawer(prospect: Prospect): void {
  drawerStack.setProspectBrowseList(filteredProspects.value)
  drawerStack.push({ kind: 'prospect', prospect })
}

/**
 * Open the prospect drawer straight on its edit form.
 * @param prospect - The prospect to edit.
 */
function openProspectEditDrawer(prospect: Prospect): void {
  drawerStack.setProspectBrowseList(filteredProspects.value)
  drawerStack.push({ kind: 'prospect', prospect, startInEdit: true })
}

/** Drawer notified 'updated' — patch the local list, or insert a freshly created prospect. */
function handleProspectUpdated(updated: Prospect): void {
  const index: number = prospects.value.findIndex((prospect: Prospect) => prospect.id === updated.id)
  if (index !== -1) prospects.value.splice(index, 1, updated)
  else prospects.value.unshift(updated)
}

/** Hidden file input used by the « Importer » dropdown. */
const importInput: Ref<HTMLInputElement | null> = ref(null)

/** Whether a JSON import is currently running. */
const isImporting: Ref<boolean> = ref(false)

/** Whether the « Importer » dropdown menu is open. */
const showImportMenu: Ref<boolean> = ref(false)

/**
 * « Importer un fichier JSON » — close the menu and open the file picker.
 */
function handleImportClick(): void {
  showImportMenu.value = false
  importInput.value?.click()
}

/**
 * « Télécharger le modèle JSON » — download the template and confirm it.
 */
function handleDownloadTemplate(): void {
  showImportMenu.value = false
  downloadProspectTemplateJson()
  toast.success('Modèle téléchargé — remplissez-le puis importez-le ici')
}

/**
 * Open the manual prospect creation drawer.
 */
function openAddProspectDrawer(): void {
  drawerStack.push({ kind: 'add-prospect' })
}

/**
 * Export the selected prospects as a JSON file (import-compatible shape).
 */
function exportSelected(): void {
  const selected: Prospect[] = prospects.value.filter((p: Prospect): boolean =>
    selectedProspects.value.includes(String(p.id)),
  )
  if (selected.length === 0) return
  downloadProspectsJson(selected)
  toast.success(
    `${selected.length} prospect${selected.length > 1 ? 's' : ''} exporté${selected.length > 1 ? 's' : ''} en JSON`,
  )
}

/**
 * Import prospects from a JSON file (see the downloadable template): each valid
 * row is created with source « manual », invalid rows are reported.
 * @param event - The file input change event.
 * @returns A promise resolved once the import completes.
 */
async function handleImportFile(event: Event): Promise<void> {
  const input: HTMLInputElement = event.target as HTMLInputElement
  const file: File | undefined = input.files?.[0]
  input.value = ''
  if (!file) return

  isImporting.value = true
  try {
    const { valid, errors }: ProspectJsonParseResult = parseProspectsJson(await file.text())
    if (valid.length === 0) {
      toast.error(errors[0] ?? 'Aucun prospect valide dans ce fichier — utilisez le modèle JSON.')
      return
    }

    let created: number = 0
    let failed: number = 0
    for (const item of valid) {
      try {
        const prospect: Prospect = await ProspectsService.createProspect({
          name: item.name,
          address: item.address || null,
          city: item.city || null,
          phone: item.phone || null,
          email: item.email || null,
          website: item.website || null,
          category: item.category ?? 'Entreprise',
          source: 'manual',
          confidence: 1,
        })
        handleProspectUpdated(prospect)
        created += 1
      } catch {
        failed += 1
      }
    }

    const skipped: number = errors.length + failed
    if (created > 0) {
      toast.success(
        `${created} prospect${created > 1 ? 's' : ''} importé${created > 1 ? 's' : ''}${skipped ? ` (${skipped} ignoré${skipped > 1 ? 's' : ''})` : ''}`,
      )
    } else {
      toast.error('Import terminé sans création — vérifiez le contenu du fichier.')
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible de lire ce fichier d'import")
  } finally {
    isImporting.value = false
  }
}

/** Drawer notified 'deleted' — remove from local list. */
function handleProspectDeleted(prospectId: number): void {
  prospects.value = prospects.value.filter((prospect: Prospect) => prospect.id !== prospectId)
  selectedProspects.value = selectedProspects.value.filter((id: string) => id !== String(prospectId))
}

// Les mutations du drawer transitent par le store : on resynchronise la liste locale.
watch(
  (): number => drawerStack.prospectMutationCounter,
  (): void => {
    const mutation: ProspectMutationNotice | null = drawerStack.lastProspectMutation
    if (!mutation) return
    if (mutation.type === 'deleted') {
      handleProspectDeleted(mutation.prospectId)
      return
    }
    handleProspectUpdated(mutation.prospect)
  },
)

/**
 * Open the quick-delete confirmation modal for a prospect.
 */
function handleDeleteProspect(prospect: Prospect): void {
  prospectToDelete.value = prospect
  deleteConfirmModal.value?.open()
}

/**
 * Delete the prospect selected in the quick-delete modal.
 */
async function confirmDeleteProspect(): Promise<void> {
  const prospect: Prospect | null = prospectToDelete.value
  if (!prospect) return
  try {
    await ProspectsService.deleteProspect(prospect.id)
    handleProspectDeleted(prospect.id)
    toast.success(`Prospect « ${prospect.name} » supprimé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    prospectToDelete.value = null
  }
}

/**
 * Delete every selected prospect, then sync the local list and the selection.
 */
async function confirmBulkDelete(): Promise<void> {
  const prospectIds: number[] = selectedIds.value
  if (bulkDeleting.value || prospectIds.length === 0) return
  bulkDeleting.value = true
  try {
    const results: PromiseSettledResult<void>[] = await Promise.allSettled(
      prospectIds.map((prospectId: number): Promise<void> => ProspectsService.deleteProspect(prospectId)),
    )
    const deletedIds: number[] = prospectIds.filter(
      (prospectId: number, index: number): boolean => results[index]?.status === 'fulfilled',
    )
    deletedIds.forEach((prospectId: number): void => handleProspectDeleted(prospectId))
    if (deletedIds.length > 0) {
      toast.success(deletedIds.length === 1 ? 'Prospect supprimé' : `${deletedIds.length} prospects supprimés`)
    }
    const failedCount: number = prospectIds.length - deletedIds.length
    if (failedCount > 0) {
      toast.error(
        failedCount === 1
          ? "1 prospect n'a pas pu être supprimé"
          : `${failedCount} prospects n'ont pas pu être supprimés`,
      )
    }
  } finally {
    bulkDeleting.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadProspects()
  // Deep-link from the dashboard hot-leads widget: ?open=<prospectId> opens the drawer.
  const openParam: LocationQueryValue | LocationQueryValue[] | undefined = useRoute().query.open
  const openId: number = Number(Array.isArray(openParam) ? openParam[0] : openParam)
  if (!Number.isNaN(openId) && openId > 0) {
    const target: Prospect | undefined = prospects.value.find((prospect: Prospect) => prospect.id === openId)
    if (target) openDrawer(target)
  }
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
