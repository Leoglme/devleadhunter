import type { ComputedRef, Ref } from 'vue'

/**
 * Live-edit overrides pushed by the dashboard's preview iframe via `postMessage`.
 *
 * The dashboard demo-site page acts as an editor: colour, photo-order and template changes are
 * applied instantly on the REAL published site (no regeneration, no reload) by merging these
 * overrides into the rendered content. Nothing is persisted here — saving still goes through the
 * API, which regenerates the published content.
 */
export type DemoPreviewOverrides = {
  templateId: string | null
  palette: Record<string, string> | null
  photos: string[] | null
}

/** Palette keys the dashboard can override — mirrors the theme contract used at generation. */
const PALETTE_KEYS: string[] = ['primary', 'secondary', 'accent']

/** Hard caps keeping a malicious or buggy message from bloating the page. */
const MAX_PHOTOS: number = 30
const MAX_PHOTO_LENGTH: number = 2_000_000
const MAX_TEMPLATE_ID_LENGTH: number = 64

/**
 * Validate and extract a template id from a raw message value.
 * @param raw - Untrusted `templateId` field of the message.
 * @returns The template id, or null when absent or invalid.
 */
function sanitizeTemplateId(raw: unknown): string | null {
  if (typeof raw !== 'string') return null
  const trimmed: string = raw.trim()
  return trimmed && trimmed.length <= MAX_TEMPLATE_ID_LENGTH ? trimmed : null
}

/**
 * Validate and extract a palette override from a raw message value.
 * @param raw - Untrusted `palette` field of the message.
 * @returns Only the known keys carrying a valid `#rrggbb` colour, or null when none survive.
 */
function sanitizePalette(raw: unknown): Record<string, string> | null {
  if (typeof raw !== 'object' || raw === null) return null
  const source: Record<string, unknown> = raw as Record<string, unknown>
  const palette: Record<string, string> = {}
  for (const key of PALETTE_KEYS) {
    const value: unknown = source[key]
    if (typeof value === 'string' && /^#[0-9A-Fa-f]{6}$/.test(value)) {
      palette[key] = value
    }
  }
  return Object.keys(palette).length > 0 ? palette : null
}

/**
 * Validate and extract a photo-order override from a raw message value.
 * @param raw - Untrusted `photos` field of the message.
 * @returns The photo URLs (https or data URIs), capped, or null when the field is not an array.
 */
function sanitizePhotos(raw: unknown): string[] | null {
  if (!Array.isArray(raw)) return null
  const photos: string[] = []
  for (const item of raw) {
    if (photos.length >= MAX_PHOTOS) break
    if (typeof item !== 'string' || item.length > MAX_PHOTO_LENGTH) continue
    if (/^(https?:\/\/|data:image\/)/.test(item)) photos.push(item)
  }
  return photos
}

/**
 * Listen for the dashboard's live-edit messages and expose the current overrides.
 *
 * Origins are deliberately not filtered: the dashboard runs from several origins (Tauri shell,
 * web build, local dev) and a rogue embedder could only restyle its OWN iframe — nothing is read
 * back, persisted, or sent anywhere. The strict shape validation above is the actual guard.
 * @param enabled - Whether live-edit mode is active (the `?_edit=1` query flag).
 * @returns The reactive overrides (all null until a first valid message arrives).
 */
export function useDemoPreviewOverrides(enabled: ComputedRef<boolean>): { overrides: Ref<DemoPreviewOverrides> } {
  const overrides: Ref<DemoPreviewOverrides> = ref<DemoPreviewOverrides>({
    templateId: null,
    palette: null,
    photos: null,
  })

  /**
   * Apply one incoming `message` event when it carries a valid live-edit payload.
   * @param event - Raw message event from any parent window.
   */
  function onMessage(event: MessageEvent): void {
    if (!enabled.value) return
    const data: unknown = event.data
    if (typeof data !== 'object' || data === null) return
    const message: Record<string, unknown> = data as Record<string, unknown>
    if (message.type !== 'dlh:preview') return
    overrides.value = {
      templateId: sanitizeTemplateId(message.templateId),
      palette: sanitizePalette(message.palette),
      photos: sanitizePhotos(message.photos),
    }
  }

  onMounted((): void => {
    window.addEventListener('message', onMessage)
  })

  onBeforeUnmount((): void => {
    window.removeEventListener('message', onMessage)
  })

  return { overrides }
}
