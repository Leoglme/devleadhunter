import type { H3Event } from 'h3'

/** Channel stamped on the redirect target, read by `DemoBeaconUtils.channelFromQuery`. */
const SMS_CHANNEL: string = 'sms'

/**
 * SMS short link, mounted at `/s/*`: redirects `/s/<path>` to `/<path>?src=sms`.
 *
 * An SMS shows a clean branded link with no visible tracking parameter (the pattern
 * SMS providers recommend); the redirect stamps the channel so the demo or video
 * visit is still attributed to SMS. Any query already present is kept.
 * @param event - The incoming H3 request event.
 * @returns A promise that resolves once the redirect is sent.
 */
export default defineEventHandler(async (event: H3Event): Promise<void> => {
  const rawPath: string | string[] | undefined = event.context.params?.path
  const path: string = Array.isArray(rawPath) ? rawPath.join('/') : (rawPath ?? '')
  const params: URLSearchParams = new URLSearchParams(getRequestURL(event).search)
  params.set('src', SMS_CHANNEL)
  await sendRedirect(event, `/${path}?${params.toString()}`, 302)
})
