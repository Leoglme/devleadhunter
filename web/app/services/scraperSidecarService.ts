/**
 * Routes browser-driven scraping to the sidecar bundled with the desktop app.
 *
 * Google blocks datacenter IPs, so these calls must leave from the user's own
 * machine, never from the VPS. In the desktop shell the sidecar answers on
 * loopback; anywhere else (web build, dev without Tauri) the caller falls back
 * to the remote API, which is why every helper here can return `null`.
 *
 * @module services/scraperSidecarService
 */

/** Where the sidecar listens, and the token authorising a call. */
export type ScraperSidecarInfo = {
  port: number
  token: string
}

/** Chrome provisioning state reported by the sidecar. */
export type ScraperChromeState = 'ready' | 'installing' | 'unavailable' | 'unknown'

let cachedInfo: ScraperSidecarInfo | null = null

/**
 * Whether the app runs inside the Tauri desktop shell.
 * @returns True when the Tauri bridge is present.
 */
function isDesktopShell(): boolean {
  if (!import.meta.client) return false
  const runtime: Window & { __TAURI__?: unknown; __TAURI_INTERNALS__?: unknown } = window as Window & {
    __TAURI__?: unknown
    __TAURI_INTERNALS__?: unknown
  }
  return Boolean(runtime.__TAURI__ || runtime.__TAURI_INTERNALS__)
}

/**
 * Ask the Rust side where the sidecar is listening.
 *
 * @returns The sidecar coordinates, or `null` outside the desktop app or when
 * the sidecar failed to start (the caller then uses the remote API).
 */
export async function getScraperSidecarInfo(): Promise<ScraperSidecarInfo | null> {
  if (cachedInfo) return cachedInfo
  if (!isDesktopShell()) return null
  try {
    const { invoke }: { invoke: <T>(cmd: string) => Promise<T> } = await import('@tauri-apps/api/core')
    cachedInfo = await invoke<ScraperSidecarInfo>('scraper_sidecar_info')
    return cachedInfo
  } catch {
    // Sidecar absent (build web, ou démarrage échoué) → repli sur l'API distante.
    return null
  }
}

/**
 * POST a payload to the local sidecar.
 *
 * @param path - Sidecar path, e.g. `/scraper/enrich`.
 * @param payload - JSON body.
 * @param options - `timeoutMs` aborts a call the sidecar never answers (a wedged
 * browser scrape would otherwise hang the caller forever).
 * @returns The parsed response, or `null` when no sidecar is available.
 * @throws With the sidecar's message when it answers an error, or a plain
 * "ne répond pas" message when the timeout fires.
 */
export async function postToScraperSidecar<T>(
  path: string,
  payload: unknown,
  options: { timeoutMs?: number } = {},
): Promise<T | null> {
  const info: ScraperSidecarInfo | null = await getScraperSidecarInfo()
  if (!info) return null

  const controller: AbortController = new AbortController()
  const timer: ReturnType<typeof setTimeout> | null = options.timeoutMs
    ? setTimeout((): void => controller.abort(), options.timeoutMs)
    : null
  let response: Response
  try {
    response = await fetch(`http://127.0.0.1:${info.port}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Sidecar-Token': info.token },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
  } catch (err: unknown) {
    if (controller.signal.aborted) {
      throw new Error('Le scraper local ne répond pas (délai dépassé) — vérifiez que Chrome peut démarrer.')
    }
    throw err
  } finally {
    if (timer) clearTimeout(timer)
  }

  if (!response.ok) {
    const raw: string = await response.text().catch((): string => '')
    let message: string = `Recherche impossible (${response.status})`
    try {
      message = (JSON.parse(raw).detail as string) || message
    } catch {
      if (raw) message = raw
    }
    throw new Error(message)
  }
  return (await response.json()) as T
}

/**
 * Chrome provisioning state, so the UI can explain a first-launch download
 * instead of showing an empty result.
 *
 * @returns The reported state, or `unknown` when the sidecar is unreachable.
 */
export async function getScraperChromeState(): Promise<ScraperChromeState> {
  const info: ScraperSidecarInfo | null = await getScraperSidecarInfo()
  if (!info) return 'unknown'
  try {
    const response: Response = await fetch(`http://127.0.0.1:${info.port}/health`)
    if (!response.ok) return 'unknown'
    const body: { chrome?: ScraperChromeState } = await response.json()
    return body.chrome ?? 'unknown'
  } catch {
    return 'unknown'
  }
}
