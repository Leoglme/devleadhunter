/** How the user can obtain the clip. */
export type PresenterVideoCaptureMode = 'record' | 'import'

export type PresenterVideoConfigEmits = {
  'has-video': [hasVideo: boolean]
}

/** One part of the video timeline bar (intro / site / Storyblok / outro). */
export type PresenterVideoTimelineSegment = {
  key: string
  label: string
  shortLabel: string
  seconds: number
  /** CSS width of the bar segment, proportional to its duration. */
  width: string
  /** Tailwind classes giving the segment its grayscale tone. */
  tone: string
}
