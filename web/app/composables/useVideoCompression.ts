/**
 * Composable re-encoding an imported clip to the montage canvas, in the browser.
 *
 * The API composes at 1280x720, so downscaling here costs no final quality.
 * Re-encoding runs in real time and never throws: a failed attempt hands the
 * original back with a reason, and the caller checks whether it still fits.
 *
 * @module composables/useVideoCompression
 */

import type { Ref } from 'vue'
import { ref } from 'vue'
import { extensionForRecorderMimeType, resolveRecorderMimeType } from '~/composables/useWebcamRecorder'

/** ⚠️ Mirrors `client_max_body_size` on the API vhost — keep both in sync. */
export const PRESENTER_VIDEO_MAX_BYTES: number = 100 * 1024 * 1024

/** Above this size, re-encoding in the browser is quicker than uploading as-is. */
const COMPRESSION_THRESHOLD_BYTES: number = 60 * 1024 * 1024

/** Montage canvas: the API composes at 1280x720, anything larger is thrown away. */
const TARGET_WIDTH: number = 1280
const TARGET_HEIGHT: number = 720

/** Bitrate caps — same budget as the in-app recorder. */
const VIDEO_BITS_PER_SECOND: number = 2_500_000
const AUDIO_BITS_PER_SECOND: number = 128_000

/** How often the recorder flushes a chunk, in ms. */
const CHUNK_INTERVAL_MS: number = 250

/** Give up on a source whose metadata never arrives (exotic MOV/MKV codec). */
const METADATA_TIMEOUT_MS: number = 15_000

/** Why a clip was handed back untouched. */
export type VideoCompressionSkipReason =
  | 'below-threshold'
  | 'undecodable'
  | 'unknown-duration'
  | 'recorder-unavailable'
  | 'no-gain'

/** Outcome of a compression attempt — never throws, always yields a usable file. */
export type VideoCompressionResult = {
  file: File
  wasCompressed: boolean
  originalBytes: number
  skipReason: VideoCompressionSkipReason | null
}

export type UseVideoCompressionReturn = {
  isCompressing: Ref<boolean>
  compressionProgress: Ref<number>
  compressPresenterClip: (file: File) => Promise<VideoCompressionResult>
}

/** A media element exposing the non-standard capture API (Chromium / Firefox). */
type CapturableVideoElement = HTMLVideoElement & {
  captureStream?: () => MediaStream
  mozCaptureStream?: () => MediaStream
}

/**
 * Read a source's duration, or give up when the browser cannot decode it.
 *
 * A `.mov` carrying HEVC or an exotic `.mkv` never fires `loadedmetadata` in
 * Chromium — hence the timeout rather than an open-ended wait.
 *
 * @param video - Detached video element to load the source into.
 * @param sourceUrl - Object URL of the picked file.
 * @returns The duration in seconds, or `null` when undecodable or unbounded.
 */
function loadVideoDuration(video: HTMLVideoElement, sourceUrl: string): Promise<number | null> {
  return new Promise((resolve: (value: number | null) => void): void => {
    const settle: (value: number | null) => void = (value: number | null): void => {
      window.clearTimeout(timeoutId)
      video.onloadedmetadata = null
      video.onerror = null
      resolve(value)
    }
    const timeoutId: number = window.setTimeout((): void => settle(null), METADATA_TIMEOUT_MS)

    video.onloadedmetadata = (): void => {
      const duration: number = video.duration
      settle(Number.isFinite(duration) && duration > 0 ? duration : null)
    }
    video.onerror = (): void => settle(null)

    video.preload = 'auto'
    video.muted = false
    video.volume = 0
    video.playsInline = true
    video.src = sourceUrl
  })
}

/**
 * Fit a source into the montage canvas without distorting it or upscaling.
 * @param sourceWidth - Intrinsic width of the source.
 * @param sourceHeight - Intrinsic height of the source.
 * @returns Even-numbered canvas dimensions (odd sizes break some encoders).
 */
function computeTargetSize(sourceWidth: number, sourceHeight: number): { width: number; height: number } {
  const scale: number = Math.min(TARGET_WIDTH / sourceWidth, TARGET_HEIGHT / sourceHeight, 1)
  const toEven: (value: number) => number = (value: number): number => Math.max(2, Math.round(value / 2) * 2)
  return { width: toEven(sourceWidth * scale), height: toEven(sourceHeight * scale) }
}

/**
 * Grab the audio track of a playing source, when the engine exposes capture.
 * @param video - The playing source element.
 * @returns Its audio tracks, or an empty array for a silent (or uncapturable) clip.
 */
function captureAudioTracks(video: CapturableVideoElement): MediaStreamTrack[] {
  const capture: (() => MediaStream) | undefined = video.captureStream ?? video.mozCaptureStream
  if (!capture) return []
  try {
    return capture.call(video).getAudioTracks()
  } catch {
    // A source without an audio track throws on some engines — silent is fine.
    return []
  }
}

/**
 * Play the source through a canvas and record it at the montage resolution.
 *
 * Runs in real time: the recorder is fed by `canvas.captureStream()`, so frames
 * only exist as fast as the source plays.
 *
 * @param video - Loaded source element (metadata already available).
 * @param duration - Source duration in seconds, used for progress.
 * @param progress - Ref updated from 0 to 1 while encoding.
 * @returns The re-encoded blob.
 * @throws When the canvas context or the recorder cannot be created.
 */
function encodeToCanvas(video: CapturableVideoElement, duration: number, progress: Ref<number>): Promise<Blob> {
  const { width, height }: { width: number; height: number } = computeTargetSize(video.videoWidth, video.videoHeight)
  const canvas: HTMLCanvasElement = document.createElement('canvas')
  canvas.width = width
  canvas.height = height

  const context: CanvasRenderingContext2D | null = canvas.getContext('2d')
  if (!context) throw new Error('Canvas 2D indisponible')

  const stream: MediaStream = canvas.captureStream(30)
  for (const track of captureAudioTracks(video)) stream.addTrack(track)

  const mimeType: string = resolveRecorderMimeType()
  const recorder: MediaRecorder = new MediaRecorder(stream, {
    ...(mimeType ? { mimeType } : {}),
    videoBitsPerSecond: VIDEO_BITS_PER_SECOND,
    audioBitsPerSecond: AUDIO_BITS_PER_SECOND,
  })

  const chunks: Blob[] = []
  recorder.ondataavailable = (event: BlobEvent): void => {
    if (event.data.size > 0) chunks.push(event.data)
  }

  return new Promise((resolve: (blob: Blob) => void, reject: (error: Error) => void): void => {
    let frameHandle: number | null = null

    const stopTracks: () => void = (): void => {
      for (const track of stream.getTracks()) track.stop()
      if (frameHandle !== null) window.cancelAnimationFrame(frameHandle)
    }

    recorder.onstop = (): void => {
      stopTracks()
      resolve(new Blob(chunks, { type: recorder.mimeType || mimeType || 'video/webm' }))
    }
    recorder.onerror = (): void => {
      stopTracks()
      reject(new Error("Échec de l'encodage du clip"))
    }

    /** Paint the frame currently decoded, until the source ends. */
    const drawFrame: () => void = (): void => {
      if (video.ended || video.paused) return
      context.drawImage(video, 0, 0, width, height)
      progress.value = Math.min(1, video.currentTime / duration)
      frameHandle = window.requestAnimationFrame(drawFrame)
    }

    video.onended = (): void => {
      // The last chunk is flushed by `stop()`, which fires `onstop` above.
      if (recorder.state !== 'inactive') recorder.stop()
    }

    video
      .play()
      .then((): void => {
        recorder.start(CHUNK_INTERVAL_MS)
        frameHandle = window.requestAnimationFrame(drawFrame)
      })
      .catch((error: unknown): void => {
        stopTracks()
        reject(error instanceof Error ? error : new Error('Lecture du clip impossible'))
      })
  })
}

/**
 * Browser-side compression of the presenter clip onto the montage canvas.
 * @returns Compression state plus the one-shot {@link compressPresenterClip}.
 */
export function useVideoCompression(): UseVideoCompressionReturn {
  const isCompressing: Ref<boolean> = ref(false)
  const compressionProgress: Ref<number> = ref(0)

  /**
   * Re-encode a picked clip to 720p, or hand it back untouched with a reason.
   * @param file - The clip the user dropped or picked.
   * @returns The file to upload, compressed when it was worth it.
   */
  async function compressPresenterClip(file: File): Promise<VideoCompressionResult> {
    const untouched: (reason: VideoCompressionSkipReason) => VideoCompressionResult = (
      reason: VideoCompressionSkipReason,
    ): VideoCompressionResult => ({
      file,
      wasCompressed: false,
      originalBytes: file.size,
      skipReason: reason,
    })

    if (file.size <= COMPRESSION_THRESHOLD_BYTES) return untouched('below-threshold')
    if (typeof MediaRecorder === 'undefined' || typeof document === 'undefined') {
      return untouched('recorder-unavailable')
    }

    isCompressing.value = true
    compressionProgress.value = 0

    const sourceUrl: string = URL.createObjectURL(file)
    const video: CapturableVideoElement = document.createElement('video') as CapturableVideoElement

    try {
      const duration: number | null = await loadVideoDuration(video, sourceUrl)
      if (duration === null) return untouched('undecodable')
      if (!video.videoWidth || !video.videoHeight) return untouched('unknown-duration')

      const compressed: Blob = await encodeToCanvas(video, duration, compressionProgress)

      // A source already lighter than our budget gains nothing from re-encoding.
      if (compressed.size >= file.size) return untouched('no-gain')

      const mimeType: string = compressed.type || 'video/webm'
      const baseName: string = file.name.replace(/\.[^./\\]+$/, '') || 'presenter'
      const optimised: File = new File([compressed], `${baseName}-720p.${extensionForRecorderMimeType(mimeType)}`, {
        type: mimeType,
      })
      return { file: optimised, wasCompressed: true, originalBytes: file.size, skipReason: null }
    } catch {
      // Never block the import on a compression failure: the caller checks the size.
      return untouched('undecodable')
    } finally {
      video.pause()
      video.removeAttribute('src')
      video.load()
      URL.revokeObjectURL(sourceUrl)
      isCompressing.value = false
      compressionProgress.value = 0
    }
  }

  return { isCompressing, compressionProgress, compressPresenterClip }
}
