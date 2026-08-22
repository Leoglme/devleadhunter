/**
 * Fire-and-forget beacons to the DevLeadHunter API for notify-worthy demo events,
 * plus the owner-visit guard shared by the demo and video trackers.
 */
export class DemoBeaconUtils {
  /**
   * Whether the current visit is the owner's own — excluded from tracking and beacons.
   * @returns True when the URL carries ?internal=1 or ?_edit=1.
   */
  static isInternalVisit(): boolean {
    if (!import.meta.client) {
      return false
    }
    const params: URLSearchParams = new URLSearchParams(window.location.search)
    return params.get('internal') === '1' || params.get('_edit') === '1'
  }

  /**
   * Beacon a demo/video behavioural event to the notifications endpoint (best-effort).
   * @param apiBase - DevLeadHunter API base URL.
   * @param slug - Demo slug identifying the prospect.
   * @param event - Event name (e.g. 'demo_cta_click').
   * @param extra - Optional context (label, host, seconds, max_scroll).
   */
  static send(apiBase: string, slug: string, event: string, extra: Record<string, unknown> = {}): void {
    if (!import.meta.client || !apiBase || !slug) {
      return
    }
    fetch(`${apiBase}/api/v1/demo-events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ demo_slug: slug, event, ...extra }),
      keepalive: true,
    }).catch((): void => {})
  }
}
