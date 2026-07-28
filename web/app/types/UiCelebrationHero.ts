/**
 * Props of the reusable `UiCelebrationHero` component.
 */

/** Heading element rendered for the celebration title. */
export type CelebrationHeadingTag = 'h1' | 'h2'

/** Props of the `UiCelebrationHero` component. */
export type UiCelebrationHeroProps = {
  title: string
  subtitle: string
  icon: string
  headingTag: CelebrationHeadingTag
  celebrate: boolean
}
