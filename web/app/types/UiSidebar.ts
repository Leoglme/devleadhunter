export type UiSidebarProps = {
  isOpen: boolean
  isMobile: boolean
}

/** One navigation entry of the dashboard sidebar. */
export type UiSidebarLink = {
  to: string
  label: string
  icon: string
  /** When set, the link only shows if that API module (e.g. `apple_wallet`) is active. */
  moduleKey?: string
}

/** A titled group of sidebar navigation entries. */
export type UiSidebarGroup = {
  heading: string | null
  links: UiSidebarLink[]
}

/** Identifier of a DevLeadHunter product module. */
export type DlhModuleKey = 'websites' | 'wallet-cards' | 'freelance-missions'

/** One entry of the module switcher (the shell hosts three activatable modules). */
export type DlhModuleEntry = {
  key: DlhModuleKey
  label: string
  icon: string
  locked: boolean
  /** The API module value (e.g. `apple_wallet`) this entry activates; absent for not-yet-built modules. */
  apiModule?: string
}
