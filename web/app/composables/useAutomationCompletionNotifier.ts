import type { UseAutomationCompletionNotifierReturn, UseToastReturn } from '~/types/Composables'
import type { AutomationStatus } from '~/types/Automation'
import { useAutomationsStore } from '~/stores/automations'
import { useToast } from '~/composables/useToast'

/** Poll cadence for the background automatisation watcher (ms). */
const POLL_INTERVAL_MS: number = 7000

/**
 * Watch automatisations in the background (across every dashboard page) and toast
 * the user when one finishes or fails — so a completion is noticed even after they
 * navigate away. Mounted once from the dashboard layout.
 *
 * @returns Start/stop controls for the background watcher.
 */
export function useAutomationCompletionNotifier(): UseAutomationCompletionNotifierReturn {
  const store: ReturnType<typeof useAutomationsStore> = useAutomationsStore()
  const toast: UseToastReturn = useToast()

  /** Last status seen per automatisation, to fire a toast only on a real transition. */
  const lastSeenStatus: Map<number, AutomationStatus> = new Map<number, AutomationStatus>()
  /** The first pass only records a baseline: it must not toast already-finished runs. */
  let hasSeededBaseline: boolean = false
  let pollHandle: ReturnType<typeof setInterval> | null = null

  /**
   * Compare the store's automatisations to the last seen statuses and toast the
   * ones that just reached a terminal state (a cancellation is user-driven — no toast).
   */
  function notifyTerminalTransitions(): void {
    for (const automation of store.automations) {
      const previousStatus: AutomationStatus | undefined = lastSeenStatus.get(automation.id)
      lastSeenStatus.set(automation.id, automation.status)
      if (!hasSeededBaseline || previousStatus === undefined || previousStatus === automation.status) {
        continue
      }
      if (automation.status === 'completed') {
        toast.success(`Automatisation « ${automation.name} » terminée`)
      } else if (automation.status === 'failed') {
        toast.error(`Automatisation « ${automation.name} » en échec`)
      }
    }
    hasSeededBaseline = true
  }

  /**
   * One watcher tick: refresh the list while a run is active (or to seed the baseline),
   * then toast any terminal transition. A transient fetch failure is ignored — the next
   * tick retries.
   * @returns A promise resolved once the tick completed.
   */
  async function poll(): Promise<void> {
    // Fetch to seed the baseline, while a run is active, or to retry after a failed poll
    // (fetchAll empties the list on error — without the retry the watcher would stall).
    if (!hasSeededBaseline || store.hasActive || store.error !== null) {
      await store.fetchAll().catch((): void => {})
    }
    notifyTerminalTransitions()
  }

  /** Start the background watcher (client only, idempotent). */
  function start(): void {
    if (!import.meta.client || pollHandle !== null) {
      return
    }
    void poll()
    pollHandle = setInterval((): void => void poll(), POLL_INTERVAL_MS)
  }

  /** Stop the background watcher. */
  function stop(): void {
    if (pollHandle !== null) {
      clearInterval(pollHandle)
      pollHandle = null
    }
  }

  return { start, stop }
}
