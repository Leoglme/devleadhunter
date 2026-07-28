/**
 * Props & simulation types of the reusable `UiCelebrationBurst` component.
 */

/** Visual family of a confetti particle. */
export type CelebrationParticleShape = 'rectangle' | 'strip' | 'dot'

/** A single confetti particle simulated on the canvas. */
export type CelebrationParticle = {
  x: number
  y: number
  velocityX: number
  velocityY: number
  rotationRad: number
  rotationSpeedRad: number
  tumblePhaseRad: number
  tumbleSpeedRad: number
  wobblePhaseRad: number
  wobbleSpeedRad: number
  wobbleAmplitude: number
  width: number
  height: number
  shape: CelebrationParticleShape
  color: string
  ageMs: number
  lifetimeMs: number
}

/** One timed wave of particles fired by the burst. */
export type CelebrationBurstWave = {
  delayMs: number
  particleCount: number
  minSpeed: number
  maxSpeed: number
}

/** A design token resolved into the confetti palette, with its draw weight. */
export type CelebrationPaletteToken = {
  token: string
  weight: number
}

/** Viewport point confetti erupts from, in CSS pixels. */
export type CelebrationBurstOrigin = {
  x: number
  y: number
}

/** Props of the `UiCelebrationBurst` component. */
export type UiCelebrationBurstProps = {
  anchor: HTMLElement | null
  active: boolean
}
