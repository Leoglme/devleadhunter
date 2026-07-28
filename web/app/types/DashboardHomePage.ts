/** One clickable stage of the pipeline strip. */
export type PipelineTile = {
  label: string
  value: string
  hint: string
  icon: string
  to: string
  linkLabel: string
}

/** One shortcut of the quick-actions card, with its accent color classes. */
export type QuickLinkShortcut = {
  to: string
  label: string
  hint: string
  icon: string
  iconColorClass: string
  iconBackgroundClass: string
}

/** One bar of the compact conversion funnel. */
export type FunnelBarStage = {
  label: string
  value: number
  widthPct: number
  stepRate: number
  color: string
}
