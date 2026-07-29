/**
 * Props of the `UiDrawerBrowseNav` component — the « Précédent / position / Suivant »
 * strip that lets a drawer step through the list the calling page displays.
 */
export type UiDrawerBrowseNavProps = {
  positionLabel: string
  canPrevious: boolean
  canNext: boolean
}
