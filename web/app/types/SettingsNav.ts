export type SettingsNavLink = {
  to: string
  label: string
  icon: string
  adminOnly?: boolean
}

export type SettingsNavGroup = {
  heading: string
  entries: SettingsNavLink[]
  adminOnly?: boolean
}
