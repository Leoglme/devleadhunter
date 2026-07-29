/**
 * Types of the `UiFilterTabs` component — the compact underlined tab row used to
 * slice a list in place, as opposed to the segmented `UiTabs` used for choices
 * that deserve their own card.
 */

/** One tab of the row. */
export type UiFilterTab = {
  key: string
  label: string
  /** Optional badge, e.g. how many items the tab holds. */
  count?: number
}

/** Props of the `UiFilterTabs` component. */
export type UiFilterTabsProps = {
  tabs: UiFilterTab[]
  modelValue: string
}
