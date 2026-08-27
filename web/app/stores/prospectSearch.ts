import type { UseScrapingJobStreamReturn } from '~/types/Composables'
/** Shared prospect-search store — one scraping job lifecycle for drawer + results page. */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useRuntimeConfig } from '#app'
import { useUserStore } from '~/stores/user'
import { useScrapingJobStream } from '~/composables/useScrapingJobStream'
import type { ScrapingJobProgressState } from '~/composables/useScrapingJobStream'
import type { Prospect } from '~/types'
import { EnrichmentService } from '~/services/enrichmentService'
import type { ProspectEnrichment } from '~/services/enrichmentService'
import { ProspectsService } from '~/services/prospectsService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import type { ScraperSidecarInfo } from '~/services/scraperSidecarService'

/** A scraping job as returned by the API. */
export type ScrapingJob = {
  id: string
  user_id: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  category: string | null
  city: string | null
  max_results: number
  source: string | null
  skip_duplicates: boolean
  only_without_website: boolean
  progress: ScrapingJobProgressState
  logs?: string[]
  live_prospects?: Prospect[]
  results: number[]
  skipped_duplicates: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

/** Parameters for starting a search. */
export type ProspectSearchParams = {
  category: string
  city: string
  maxResults: number
  source: string
  skipDuplicates: boolean
  onlyWithoutWebsite: boolean
}

/** Progress of the enrich-and-match pass chained after a Facebook search. */
export type FacebookAutoEnrichState = {
  running: boolean
  /** Candidates processed so far (enriched, rejected or removed as surplus). */
  completed: number
  /** Candidates the search discovered (the job overshoots on purpose). */
  total: number
  /** Usable prospects kept — email present, website per the checkbox. */
  kept: number
  /** Matches asked by the user (the search form's max results). */
  needed: number
  /** Candidates rejected and excluded from future searches (no email / has a website). */
  rejected: number
  /** Candidates whose enrichment failed — kept unfiltered, retryable later. */
  failed: number
  error: string | null
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useProspectSearchStore = defineStore('prospectSearch', () => {
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const stream: UseScrapingJobStreamReturn = useScrapingJobStream()

  const currentJob: Ref<ScrapingJob | null> = ref(null)
  const recentJobs: Ref<ScrapingJob[]> = ref([])
  const isStarting: Ref<boolean> = ref(false)
  const isCancelling: Ref<boolean> = ref(false)
  const isRefreshing: Ref<boolean> = ref(false)
  const completedSignal: Ref<number> = ref(0)
  const autoEnrich: Ref<FacebookAutoEnrichState | null> = ref(null)
  /** Jobs whose chained enrichment already ran — completion is signalled twice (stream + poll). */
  const autoEnrichedJobIds: Set<string> = new Set()

  let pollInterval: ReturnType<typeof setInterval> | null = null

  const liveProgress: ComputedRef<ScrapingJobProgressState> = computed((): ScrapingJobProgressState => {
    if (stream.progress.value.total > 0 || stream.progress.value.current > 0) return stream.progress.value
    return currentJob.value?.progress ?? stream.progress.value
  })
  const streamLogs: ComputedRef<string[]> = computed((): string[] => stream.logs.value)
  const streamProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => stream.prospects.value)
  const streamConnected: ComputedRef<boolean> = computed((): boolean => stream.isConnected.value)
  const streamSkipped: ComputedRef<number> = computed((): number => stream.skippedDuplicates.value)

  const isSearching: ComputedRef<boolean> = computed(
    (): boolean => currentJob.value?.status === 'running' || currentJob.value?.status === 'pending',
  )

  /**
   * Build the auth header from the user's token.
   * @returns The Authorization header (empty when unauthenticated).
   */
  function authHeaders(): Record<string, string> {
    return userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}
  }

  /** Stop the background poll. */
  function stopPolling(): void {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  /** Start polling the current job's status. */
  function startPolling(): void {
    stopPolling()
    pollInterval = setInterval((): void => {
      void refreshJobStatus()
    }, 8000)
  }

  /**
   * Hydrate + connect the live stream for a job.
   * @param job - The job to stream.
   */
  function attachStream(job: ScrapingJob): void {
    stream.hydrateFromJob({
      logs: job.logs,
      live_prospects: job.live_prospects,
      progress: job.progress,
      skipped_duplicates: job.skipped_duplicates,
    })
    if (!userStore.token) return
    stream.connect(job.id, userStore.token, {
      onDone: async (summary: { skipped_duplicates: number }): Promise<void> => {
        stopPolling()
        stream.disconnect()
        await refreshJobStatus()
        if (currentJob.value) {
          currentJob.value.status = 'completed'
          currentJob.value.skipped_duplicates = summary.skipped_duplicates
        }
        completedSignal.value += 1
        if (currentJob.value) void maybeAutoEnrichFacebook(currentJob.value)
      },
      onCancelled: async (): Promise<void> => {
        stopPolling()
        stream.disconnect()
        await refreshJobStatus()
        if (currentJob.value) currentJob.value.status = 'cancelled'
        isCancelling.value = false
      },
      onError: async (): Promise<void> => {
        stopPolling()
        await refreshJobStatus()
        isCancelling.value = false
      },
    })
  }

  /**
   * Chain the local V1 enrichment + match filter right after a Facebook search.
   *
   * Facebook discovery only yields name + city + page URL (the SERP carries no
   * contact data) — the base fields the other sources deliver at discovery time
   * (email, phone, website or not) live on the Facebook page itself, which only
   * the desktop sidecar can read (logged-out, residential IP). The job therefore
   * overshoots (3× the asked count) and this pass enriches candidates one by one,
   * keeping only usable matches — email present, and no website when the search
   * asked for site-less prospects — until the asked count is reached. Rejected
   * pages are deleted AND excluded server-side so no later search re-tests them;
   * surplus untested candidates are deleted without exclusion (rediscoverable).
   * @param job - The job that just completed.
   * @returns A promise resolved once the match pass is done.
   */
  async function maybeAutoEnrichFacebook(job: ScrapingJob): Promise<void> {
    if (job.source !== 'facebook' || autoEnrichedJobIds.has(job.id)) return
    const candidates: Prospect[] = (job.live_prospects ?? []).filter((prospect: Prospect): boolean =>
      Boolean(prospect.facebook_url),
    )
    if (candidates.length === 0) return
    autoEnrichedJobIds.add(job.id)
    const state: FacebookAutoEnrichState = {
      running: true,
      completed: 0,
      total: candidates.length,
      kept: 0,
      needed: job.max_results,
      rejected: 0,
      failed: 0,
      error: null,
    }
    autoEnrich.value = state

    const sidecar: ScraperSidecarInfo | null = await getScraperSidecarInfo()
    if (!sidecar) {
      state.running = false
      state.error =
        "La lecture des pages Facebook s'exécute en local — relancez la recherche depuis l'application desktop."
      return
    }

    for (const candidate of candidates) {
      if (state.kept >= state.needed) {
        // Surplus candidate, never tested — removed; a future search can rediscover it.
        try {
          await ProspectsService.deleteProspect(candidate.id)
        } catch {
          // Non-critical: an extra empty prospect is annoying but harmless.
        }
        state.completed += 1
        continue
      }
      try {
        const record: ProspectEnrichment = await EnrichmentService.runProspectEnrichment(
          candidate.id,
          candidate.name,
          candidate.city ?? '',
          candidate.google_maps_url ?? '',
          candidate.facebook_url ?? '',
        )
        if (record.status !== 'completed') {
          // Scrape failed — keep the prospect unfiltered so a manual retry stays possible.
          state.failed += 1
          state.completed += 1
          continue
        }
        const fresh: Prospect = await ProspectsService.getProspect(candidate.id)
        const usable: boolean = Boolean(fresh.email) && (!job.only_without_website || !fresh.website)
        if (usable) {
          state.kept += 1
        } else {
          state.rejected += 1
          await ProspectsService.deleteProspect(candidate.id)
          await ProspectsService.excludeFacebookPage(
            candidate.facebook_url ?? '',
            fresh.email ? 'has_website' : 'no_email',
          )
        }
      } catch {
        state.failed += 1
      }
      state.completed += 1
    }
    state.running = false
  }

  /**
   * Refresh the current job's status from the API.
   * @returns A promise resolved once refreshed.
   */
  async function refreshJobStatus(): Promise<void> {
    if (!currentJob.value) return
    try {
      isRefreshing.value = true
      const response: ScrapingJob = await $fetch<ScrapingJob>(
        `${config.public.apiBase}/api/v1/scraping-jobs/${currentJob.value.id}`,
        { method: 'GET', headers: authHeaders() },
      )
      const wasDone: boolean = currentJob.value.status === 'completed'
      currentJob.value = response
      if (response.status === 'completed' || response.status === 'failed' || response.status === 'cancelled') {
        stopPolling()
        isCancelling.value = false
        await loadRecent()
        if (response.status === 'completed' && !wasDone) {
          completedSignal.value += 1
          void maybeAutoEnrichFacebook(response)
        }
      }
    } catch {
      // Ignore transient refresh errors.
    } finally {
      isRefreshing.value = false
    }
  }

  /**
   * Start a new search.
   * @param params - The search parameters.
   * @returns A promise resolved once the job is created.
   */
  async function startSearch(params: ProspectSearchParams): Promise<void> {
    isStarting.value = true
    try {
      const response: ScrapingJob = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: {
          category: params.category || null,
          city: params.city || null,
          max_results: params.maxResults,
          source: params.source || null,
          skip_duplicates: params.skipDuplicates,
          only_without_website: params.onlyWithoutWebsite,
        },
      })
      currentJob.value = response
      autoEnrich.value = null
      stream.reset()
      attachStream(response)
      startPolling()
    } finally {
      isStarting.value = false
    }
  }

  /**
   * Cancel the current running search (e.g. launched by mistake).
   * The scrape stops gracefully; prospects already found are kept.
   * @returns A promise resolved once the cancel request is acknowledged.
   */
  async function cancelSearch(): Promise<void> {
    const job: ScrapingJob | null = currentJob.value
    if (!job || (job.status !== 'running' && job.status !== 'pending')) return
    isCancelling.value = true
    try {
      await $fetch(`${config.public.apiBase}/api/v1/scraping-jobs/${job.id}/cancel`, {
        method: 'POST',
        headers: authHeaders(),
      })
      // The job flips to 'cancelled' via the stream ('cancelled') or the poll.
    } catch {
      isCancelling.value = false
    }
  }

  /**
   * Load a specific job by id and stream it.
   * @param jobId - The job id.
   * @returns A promise resolved once loaded.
   */
  async function loadJob(jobId: string): Promise<void> {
    const response: ScrapingJob = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs/${jobId}`, {
      method: 'GET',
      headers: authHeaders(),
    })
    currentJob.value = response
    stream.reset()
    attachStream(response)
    if (response.status === 'running' || response.status === 'pending') startPolling()
  }

  /**
   * Load the user's recent jobs (and adopt a running one if idle).
   * @returns A promise resolved once loaded.
   */
  async function loadRecent(): Promise<void> {
    try {
      const response: ScrapingJob[] = await $fetch<ScrapingJob[]>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
        method: 'GET',
        headers: authHeaders(),
      })
      recentJobs.value = [...response]
        .sort(
          (a: ScrapingJob, b: ScrapingJob): number =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
        .slice(0, 5)
      if (!currentJob.value) {
        const running: ScrapingJob | undefined = recentJobs.value.find(
          (j: ScrapingJob): boolean => j.status === 'running',
        )
        if (running) {
          currentJob.value = running
          stream.reset()
          attachStream(running)
          startPolling()
        }
      }
    } catch {
      // Ignore — recent jobs are non-critical.
    }
  }

  /** Clear the current job and disconnect the stream. */
  function reset(): void {
    currentJob.value = null
    autoEnrich.value = null
    stream.disconnect()
    stream.reset()
    stopPolling()
  }

  return {
    currentJob,
    recentJobs,
    isStarting,
    isCancelling,
    isRefreshing,
    completedSignal,
    autoEnrich,
    liveProgress,
    streamLogs,
    streamProspects,
    streamConnected,
    streamSkipped,
    isSearching,
    startSearch,
    cancelSearch,
    refreshJobStatus,
    loadJob,
    loadRecent,
    reset,
  }
})
