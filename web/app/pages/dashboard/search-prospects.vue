<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
      <div>
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Trouver des prospects</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
          Le formulaire s'ouvre dans un volet — les résultats s'affichent ici. La recherche continue en arrière-plan.
        </p>
      </div>
      <button class="app-btn-primary h-9 px-4 text-xs" @click="openSearchDrawer">
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
        Nouvelle recherche
      </button>
    </div>

    <div v-if="!store.currentJob" class="app-card px-6 py-14 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Lancez une recherche</h3>
      <p class="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[var(--app-ink-soft)]">
        Décrivez un métier et une ville dans le volet — DevLeadHunter trouve les artisans qui correspondent.
      </p>
      <button class="app-btn-primary mx-auto mt-6 inline-flex" @click="openSearchDrawer">
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
        Ouvrir le formulaire
      </button>
    </div>

    <div v-else class="app-card p-5 md:p-6">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-[var(--app-ink)]">
            Recherche
            <span v-if="store.currentJob.status === 'completed'" class="ml-2 text-[var(--app-green)]">✓ Terminée</span>
            <span v-else-if="store.currentJob.status === 'cancelled'" class="ml-2 text-[var(--app-ink-soft)]">
              ⊘ Annulée
            </span>
            <span v-else-if="store.currentJob.status === 'failed'" class="ml-2 text-[var(--app-red)]">✗ Échec</span>
          </h2>
          <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
            {{ store.currentJob.category }} · {{ store.currentJob.city }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="store.isRefreshing"
            class="app-btn-secondary h-8 px-3 text-xs disabled:opacity-50"
            @click="store.refreshJobStatus()"
          >
            <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', store.isRefreshing && 'animate-spin']" />
            Actualiser
          </button>
          <button class="app-btn-primary h-8 px-3 text-xs" @click="openSearchDrawer">Nouvelle recherche</button>
        </div>
      </div>

      <div v-if="store.isSearching" class="space-y-4">
        <div>
          <div class="mb-2 flex items-center justify-between text-sm">
            <span class="font-medium text-[var(--app-ink-soft)]">
              {{ store.displayProgress.current }} /
              {{ store.displayProgress.total || store.currentJob.max_results }} ajoutés
            </span>
            <div class="flex items-center gap-3">
              <button
                type="button"
                class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-red)] transition-opacity hover:opacity-80 disabled:opacity-50"
                :disabled="store.isCancelling"
                @click="store.cancelSearch()"
              >
                <UIcon
                  :name="store.isCancelling ? 'i-lucide-loader-circle' : 'i-lucide-circle-stop'"
                  :class="['h-3.5 w-3.5', store.isCancelling && 'animate-spin']"
                />
                {{ store.isCancelling ? 'Annulation…' : 'Annuler' }}
              </button>
              <span class="font-medium text-[var(--app-ink-soft)]"
                >{{ Math.round(store.displayProgress.percentage) }}%</span
              >
            </div>
          </div>
          <div class="h-3 w-full overflow-hidden rounded-full border border-[var(--app-line)] bg-[var(--app-bg)]">
            <div
              class="h-full rounded-full bg-[var(--app-ink)] transition-all duration-300"
              :style="{ width: Math.min(store.displayProgress.percentage, 100) + '%' }"
            />
          </div>
        </div>
        <div
          v-if="store.displayProgress.current_prospect"
          class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
        >
          <p class="text-sm text-[var(--app-ink)]">
            <span class="font-medium">En cours :</span> {{ store.displayProgress.current_prospect }}
          </p>
        </div>
        <ScrapingJobLivePanel
          :logs="store.streamLogs"
          :prospects="store.currentJob.source === 'facebook' ? store.facebookKeptProspects : store.streamProspects"
          :is-running="store.currentJob.status === 'running'"
        />
      </div>

      <div
        v-else-if="store.currentJob.status === 'completed' || store.currentJob.status === 'cancelled'"
        class="space-y-4"
      >
        <p v-if="store.currentJob.status === 'cancelled'" class="text-sm text-[var(--app-ink-soft)]">
          Recherche annulée — les {{ store.currentJob.results.length }} prospect(s) déjà trouvé(s) ont été conservés.
        </p>
        <div class="grid grid-cols-1 gap-4 @3xl:grid-cols-3">
          <div
            v-for="stat in completedStats"
            :key="stat.label"
            class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4"
          >
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg" :class="stat.iconBg">
                <UIcon :name="stat.icon" class="h-5 w-5" :class="stat.iconColor" />
              </div>
              <div>
                <p class="text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ stat.value }}</p>
                <p class="text-sm text-[var(--app-ink-soft)]">{{ stat.label }}</p>
              </div>
            </div>
          </div>
        </div>
        <div v-if="store.autoEnrich" class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
          <p v-if="store.autoEnrich.running" class="flex items-center gap-2 text-sm text-[var(--app-ink)]">
            <UIcon name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            <template v-if="store.autoEnrich.chromeInstalling">
              Installation de Chrome sur ce poste (premier lancement, ~150 Mo) — la vérification démarrera ensuite…
            </template>
            <template v-else-if="store.autoEnrich.checking > 0">
              Vérification de la page {{ store.autoEnrich.checking }}/{{ store.autoEnrich.roundSize }} (~1 min par page)
              — {{ store.autoEnrich.kept }}/{{ store.autoEnrich.needed }} prospect(s) utilisable(s) trouvé(s)…
            </template>
            <template v-else>
              Préparation du navigateur — {{ store.autoEnrich.kept }}/{{ store.autoEnrich.needed }} prospect(s)
              utilisable(s) trouvé(s)…
            </template>
          </p>
          <p v-else-if="store.autoEnrich.error" class="text-sm text-[var(--app-red)]">
            Vérification interrompue : {{ store.autoEnrich.error }}
          </p>
          <p v-else-if="store.autoEnrich.exhausted" class="text-sm text-[var(--app-ink)]">
            {{ store.autoEnrich.kept }}/{{ store.autoEnrich.needed }} prospect(s) utilisable(s) — la source est épuisée
            pour cette recherche
            <span
              v-if="store.autoEnrich.tested === 0 && store.autoEnrich.knownSkipped > 0"
              class="text-[var(--app-ink-soft)]"
            >
              (les {{ store.autoEnrich.knownSkipped }} pages trouvées ont déjà été testées et rejetées par vos
              recherches précédentes — essayez une autre ville ou catégorie)
            </span>
            <span v-else class="text-[var(--app-ink-soft)]">
              ({{ store.autoEnrich.tested }} page(s) vérifiée(s) : {{ store.autoEnrich.rejectedNoEmail }} sans email,
              {{ store.autoEnrich.rejectedWebsite }} avec site web{{
                store.autoEnrich.knownSkipped > 0 ? `, ${store.autoEnrich.knownSkipped} déjà testée(s) avant` : ''
              }}
              — essayez une autre ville ou catégorie)
            </span>
            <span v-if="store.autoEnrich.failed > 0" class="text-[var(--app-red)]">
              — {{ store.autoEnrich.failed }} page(s) illisible(s){{
                store.autoEnrich.lastFailure ? ` : ${store.autoEnrich.lastFailure}` : ''
              }}
            </span>
          </p>
          <p v-else class="text-sm text-[var(--app-ink)]">
            <span class="font-medium text-[var(--app-green)]">✓</span>
            {{ store.autoEnrich.kept }}/{{ store.autoEnrich.needed }} prospect(s) utilisable(s) ajouté(s) — avec email{{
              store.currentJob.only_without_website ? ', sans site web' : ''
            }}
            <span v-if="store.autoEnrich.failed > 0" class="text-[var(--app-red)]">
              — {{ store.autoEnrich.failed }} page(s) illisible(s){{
                store.autoEnrich.lastFailure ? ` : ${store.autoEnrich.lastFailure}` : ''
              }}
            </span>
          </p>
        </div>
        <ScrapingJobLivePanel
          v-if="store.streamLogs.length > 0"
          :logs="store.streamLogs"
          :prospects="store.currentJob.source === 'facebook' ? store.facebookKeptProspects : store.streamProspects"
          :is-running="false"
        />
        <div class="flex items-center gap-3 pt-2">
          <NuxtLink to="/dashboard/my-prospects" class="app-btn-primary">Voir mes prospects</NuxtLink>
          <button class="app-btn-secondary" @click="openSearchDrawer">Nouvelle recherche</button>
        </div>
      </div>

      <div
        v-else-if="store.currentJob.status === 'failed'"
        class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]"
      >
        <p class="font-semibold">La recherche a échoué</p>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ store.currentJob.error }}</p>
        <button class="app-btn-secondary mt-4" @click="openSearchDrawer">Réessayer</button>
      </div>
    </div>

    <div v-if="store.recentJobs.length > 0" class="app-card p-5 md:p-6">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Recherches récentes</h2>
      <div class="divide-y divide-[var(--app-line-soft)]">
        <div v-for="job in store.recentJobs" :key="job.id" class="py-3 first:pt-0 last:pb-0">
          <button
            type="button"
            class="group flex w-full cursor-pointer items-center justify-between gap-3 text-left transition-colors"
            @click="toggleRecentJob(job)"
          >
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <p class="truncate text-sm font-medium text-[var(--app-ink)] capitalize">
                  {{ job.category }} · {{ job.city }}
                </p>
                <span :class="['app-badge', jobStatusVariant(job.status)]">{{ formatStatus(job.status) }}</span>
              </div>
              <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
                {{ new Date(job.created_at).toLocaleString('fr-FR') }}
                <span v-if="(job.status === 'completed' || job.status === 'cancelled') && job.source !== 'facebook'">
                  · {{ job.results.length }} prospects ajoutés
                </span>
              </p>
            </div>
            <UIcon
              :name="expandedJobId === job.id ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
              class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]"
            />
          </button>
          <div v-if="expandedJobId === job.id" class="mt-3 space-y-2">
            <p v-if="isLoadingExpanded" class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
              <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
              Chargement des prospects…
            </p>
            <p v-else-if="expandedProspects.length === 0" class="text-xs text-[var(--app-ink-soft)]">
              Aucun prospect conservé pour cette recherche (ignorés par le filtre ou supprimés depuis).
            </p>
            <template v-else>
              <div
                v-for="prospect in expandedProspects"
                :key="prospect.id"
                class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2"
              >
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span class="text-sm font-medium text-[var(--app-ink)]">{{ prospect.name }}</span>
                  <span class="text-xs text-[var(--app-ink-soft)]">{{ prospect.city || 'Ville inconnue' }}</span>
                  <a
                    v-if="prospect.website"
                    :href="prospect.website"
                    target="_blank"
                    rel="noopener"
                    class="app-badge app-badge--info"
                  >
                    Site web
                  </a>
                  <span v-else class="app-badge">Sans site</span>
                </div>
                <div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--app-ink-soft)]">
                  <span class="inline-flex items-center gap-1">
                    <UIcon name="i-lucide-mail" class="h-3 w-3" />
                    {{ prospect.email || '—' }}
                  </span>
                  <span class="inline-flex items-center gap-1">
                    <UIcon name="i-lucide-phone" class="h-3 w-3" />
                    {{ prospect.phone || '—' }}
                  </span>
                </div>
              </div>
              <NuxtLink
                to="/dashboard/my-prospects"
                class="inline-flex items-center gap-1 text-xs font-medium text-[var(--app-ink)] underline underline-offset-2"
              >
                Voir dans Mes prospects
              </NuxtLink>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { FacebookAutoEnrichState, ScrapingJob } from '~/stores/prospectSearch'
import type { CompletedStat } from '~/types/SearchProspectsPage'
import type { Prospect } from '~/types'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { ProspectsService } from '~/services/prospectsService'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

/** Stat tiles for a completed job — a Facebook match loop shows its own counters. */
const completedStats: ComputedRef<CompletedStat[]> = computed((): CompletedStat[] => {
  const job: ScrapingJob | null = store.currentJob
  if (job === null) return []
  const match: FacebookAutoEnrichState | null = store.autoEnrich
  if (job.source === 'facebook' && match) {
    // The user asked for N usable prospects — that is the only number that matters.
    return [
      {
        label: 'Prospects utilisables',
        value: match.kept,
        icon: 'i-lucide-user-check',
        iconBg: 'bg-[var(--app-green-soft)]',
        iconColor: 'text-[var(--app-green)]',
      },
    ]
  }
  return [
    {
      label: 'Prospects ajoutés',
      value: job.results.length,
      icon: 'i-lucide-user-check',
      iconBg: 'bg-[var(--app-green-soft)]',
      iconColor: 'text-[var(--app-green)]',
    },
    {
      label: 'Prospects trouvés',
      value: job.progress.total,
      icon: 'i-lucide-search',
      iconBg: 'bg-[var(--app-blue-soft)]',
      iconColor: 'text-[var(--app-blue)]',
    },
    {
      label: 'Doublons ignorés',
      value: job.skipped_duplicates,
      icon: 'i-lucide-copy-x',
      iconBg: 'bg-[var(--app-surface-2)]',
      iconColor: 'text-[var(--app-ink-soft)]',
    },
  ]
})

/** Open the search form drawer. */
function openSearchDrawer(): void {
  drawerStack.push({ kind: 'search-prospects' })
}

const expandedJobId: Ref<string | null> = ref(null)
const expandedProspects: Ref<Prospect[]> = ref([])
const isLoadingExpanded: Ref<boolean> = ref(false)

/**
 * Toggle the inline summary of a recent search — base info of each prospect found
 * (name, city, website or not, email, phone). A running search keeps the previous
 * behaviour and is loaded into the live card above instead.
 * @param job - The recent job row that was clicked.
 * @returns A promise resolved once the summary is loaded.
 */
async function toggleRecentJob(job: ScrapingJob): Promise<void> {
  if (job.status === 'running' || job.status === 'pending') {
    await store.loadJob(job.id)
    return
  }
  if (expandedJobId.value === job.id) {
    expandedJobId.value = null
    return
  }
  expandedJobId.value = job.id
  isLoadingExpanded.value = true
  expandedProspects.value = []
  try {
    const all: Prospect[] = await ProspectsService.listProspects()
    const order: Map<number, number> = new Map(
      job.results.map((id: number, index: number): [number, number] => [id, index]),
    )
    // Prospects rejected by the match filter or deleted since are gone from this list — on
    // purpose: the row must reflect what the user actually kept, not the raw snapshot.
    expandedProspects.value = all
      .filter((prospect: Prospect): boolean => order.has(prospect.id))
      .sort((a: Prospect, b: Prospect): number => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
  } catch {
    expandedProspects.value = job.live_prospects ?? []
  } finally {
    isLoadingExpanded.value = false
  }
}

/**
 * Badge variant class for a job status.
 * @param status - The status.
 * @returns The ``app-badge--*`` modifier.
 */
function jobStatusVariant(status: string): string {
  if (status === 'completed') return 'app-badge--success'
  if (status === 'failed') return 'app-badge--danger'
  if (status === 'running') return 'app-badge--info'
  return ''
}

/**
 * Human label for a job status.
 * @param status - The status.
 * @returns The French label.
 */
function formatStatus(status: string): string {
  const map: Record<string, string> = {
    pending: 'En attente',
    running: 'En cours',
    completed: 'Terminée',
    cancelled: 'Annulée',
    failed: 'Échec',
  }
  return map[status] ?? status
}

onMounted(async (): Promise<void> => {
  await store.loadRecent()
  // Open the form drawer straight away when there's nothing to show.
  if (store.currentJob === null) openSearchDrawer()
})
</script>
