import type { H3Event } from 'h3'

const POSTHOG_API_HOST: string = 'eu.i.posthog.com'
const POSTHOG_ASSETS_HOST: string = 'eu-assets.i.posthog.com'

const EXCLUDED_REQUEST_HEADERS: string[] = [
  'host',
  'connection',
  'content-length',
  'transfer-encoding',
  'accept-encoding',
]

const EXCLUDED_RESPONSE_HEADERS: string[] = ['content-encoding', 'content-length', 'transfer-encoding']

/**
 * First-party reverse proxy to PostHog EU, mounted at `/dibodev/events/*`.
 *
 * posthog-js is initialised with `api_host: '/dibodev/events'`, so it sends both
 * events and its own assets (`array/`, `static/`) through this same-origin path.
 * Serving them from demo.dibodev.fr (not eu.i.posthog.com) keeps them off the
 * tracker blocklists that Firefox ETP, Safari ITP and adblockers apply — otherwise
 * a large share of real demo visits go uncounted.
 * @param event - The incoming H3 request event.
 * @returns The proxied PostHog response body.
 * @see https://posthog.com/docs/advanced/proxy/nuxt
 */
export default defineEventHandler(async (event: H3Event): Promise<Buffer> => {
  const rawPath: string | string[] | undefined = event.context.params?.path
  const path: string = Array.isArray(rawPath) ? rawPath.join('/') : (rawPath ?? '')
  const search: string = getRequestURL(event).search || ''

  const useAssetHost: boolean = path.startsWith('static/') || path.startsWith('array/')
  const hostname: string = useAssetHost ? POSTHOG_ASSETS_HOST : POSTHOG_API_HOST
  const targetUrl: string = `https://${hostname}/${path}${search}`

  const headers: Headers = new Headers()
  const requestHeaders: Record<string, string | undefined> = getRequestHeaders(event)
  for (const [key, value] of Object.entries(requestHeaders)) {
    if (value && !EXCLUDED_REQUEST_HEADERS.includes(key.toLowerCase())) {
      headers.set(key, value)
    }
  }
  headers.set('host', hostname)

  const clientIp: string | undefined =
    getHeader(event, 'x-forwarded-for') ?? getRequestIP(event, { xForwardedFor: true }) ?? undefined
  if (clientIp) headers.set('x-forwarded-for', clientIp)

  const rawBody: Buffer | undefined =
    event.method !== 'GET' && event.method !== 'HEAD' ? await readRawBody(event, false) : undefined

  const response: Response = await fetch(targetUrl, {
    method: event.method,
    headers,
    body: rawBody ? new Uint8Array(rawBody) : undefined,
  })

  for (const [key, value] of response.headers.entries()) {
    if (!EXCLUDED_RESPONSE_HEADERS.includes(key.toLowerCase())) {
      setResponseHeader(event, key, value)
    }
  }
  setResponseStatus(event, response.status)

  return Buffer.from(await response.arrayBuffer())
})
