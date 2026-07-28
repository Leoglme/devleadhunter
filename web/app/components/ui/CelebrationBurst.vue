<template>
  <Teleport v-if="isMounted" to="body">
    <canvas v-show="isRunning" ref="canvasElement" class="pointer-events-none fixed inset-0 z-50" aria-hidden="true" />
  </Teleport>
</template>

<script lang="ts" setup>
import type { PropType, Ref } from 'vue'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type {
  CelebrationBurstOrigin,
  CelebrationBurstWave,
  CelebrationPaletteToken,
  CelebrationParticle,
  CelebrationParticleShape,
  UiCelebrationBurstProps,
} from '~/types/UiCelebrationBurst'

/**
 * Dependency-free confetti burst rendered on a full-viewport canvas.
 * Fires once when `active` turns true, from the center of `anchor`, with a
 * palette resolved from the current theme tokens. Skipped entirely when the
 * user prefers reduced motion.
 */
const props: UiCelebrationBurstProps = defineProps({
  anchor: {
    type: Object as PropType<HTMLElement | null>,
    default: null,
  },
  active: {
    type: Boolean,
    default: false,
  },
})

/** Timed waves: a big pop, an echo, then a light sprinkle for depth. */
const BURST_WAVES: CelebrationBurstWave[] = [
  { delayMs: 0, particleCount: 90, minSpeed: 6.5, maxSpeed: 12.5 },
  { delayMs: 160, particleCount: 45, minSpeed: 4.5, maxSpeed: 9 },
  { delayMs: 340, particleCount: 25, minSpeed: 3, maxSpeed: 6.5 },
]

/** Theme tokens mixed into the confetti palette, weighted by presence. */
const PALETTE_TOKENS: CelebrationPaletteToken[] = [
  { token: '--app-ink', weight: 3 },
  { token: '--app-accent', weight: 3 },
  { token: '--app-green', weight: 2 },
  { token: '--app-blue', weight: 1 },
  { token: '--app-accent-ink', weight: 1 },
]

/** Downward pull applied each 60fps-normalized step, in px. */
const GRAVITY_PER_STEP: number = 0.16
/** Velocity kept after air drag each step. */
const AIR_DRAG_PER_STEP: number = 0.988
/** Half-angle of the upward launch cone, in radians. */
const LAUNCH_CONE_HALF_ANGLE_RAD: number = 1.22
/** Share of particles thrown in a full circle instead of the upward cone. */
const RING_PARTICLE_RATIO: number = 0.22
/** Life share after which a particle starts fading out. */
const FADE_START_LIFE_RATIO: number = 0.7
/** Device-pixel-ratio cap, to keep the canvas cheap on retina screens. */
const MAX_DEVICE_PIXEL_RATIO: number = 2

/** Whether the component is mounted (gates the body teleport under SSR). */
const isMounted: Ref<boolean> = ref(false)
/** Whether the simulation currently draws frames. */
const isRunning: Ref<boolean> = ref(false)
/** The full-viewport canvas. */
const canvasElement: Ref<HTMLCanvasElement | null> = ref(null)

/** Live particles, outside reactivity on purpose: touched every frame. */
let particles: CelebrationParticle[] = []
/** Pending wave timers, cleared on unmount. */
let waveTimers: ReturnType<typeof setTimeout>[] = []
/** Current animation-frame handle. */
let frameHandle: number | null = null
/** Timestamp of the previous frame, for delta-time physics. */
let previousFrameMs: number = 0

/**
 * Random number in a range.
 * @param min - Lower bound (inclusive).
 * @param max - Upper bound (exclusive).
 * @returns A float between the bounds.
 */
function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

/**
 * Resolve the weighted confetti palette from the theme tokens visible at the
 * anchor (falls back to the document body).
 * @returns Hex/rgb color strings, repeated by weight.
 */
function resolvePalette(): string[] {
  const source: HTMLElement = props.anchor ?? document.body
  const styles: CSSStyleDeclaration = getComputedStyle(source)
  const palette: string[] = []
  PALETTE_TOKENS.forEach((entry: CelebrationPaletteToken): void => {
    const color: string = styles.getPropertyValue(entry.token).trim()
    if (!color) return
    for (let repeat: number = 0; repeat < entry.weight; repeat += 1) palette.push(color)
  })
  return palette.length > 0 ? palette : ['#1d1a14']
}

/**
 * Viewport coordinates confetti erupts from: the anchor center, or the upper
 * third of the screen when no anchor is given.
 * @returns The origin point, in CSS pixels.
 */
function resolveOrigin(): CelebrationBurstOrigin {
  const anchor: HTMLElement | null = props.anchor
  if (anchor) {
    const rect: DOMRect = anchor.getBoundingClientRect()
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
  }
  return { x: window.innerWidth / 2, y: window.innerHeight / 3 }
}

/**
 * Build one particle launched from the origin.
 * @param originX - Launch x, in CSS pixels.
 * @param originY - Launch y, in CSS pixels.
 * @param wave - The wave the particle belongs to.
 * @param palette - Colors to pick from.
 * @returns A ready-to-simulate particle.
 */
function spawnParticle(
  originX: number,
  originY: number,
  wave: CelebrationBurstWave,
  palette: string[],
): CelebrationParticle {
  const isRingParticle: boolean = Math.random() < RING_PARTICLE_RATIO
  const angleRad: number = isRingParticle
    ? randomBetween(-Math.PI, Math.PI)
    : -Math.PI / 2 + randomBetween(-LAUNCH_CONE_HALF_ANGLE_RAD, LAUNCH_CONE_HALF_ANGLE_RAD)
  const speed: number = isRingParticle
    ? randomBetween(wave.minSpeed * 0.4, wave.minSpeed)
    : randomBetween(wave.minSpeed, wave.maxSpeed)
  const shapeRoll: number = Math.random()
  const shape: CelebrationParticleShape = shapeRoll < 0.5 ? 'rectangle' : shapeRoll < 0.8 ? 'strip' : 'dot'
  const width: number = shape === 'strip' ? randomBetween(2.5, 3.5) : randomBetween(5, 8)
  const height: number = shape === 'strip' ? randomBetween(11, 16) : shape === 'dot' ? width : randomBetween(8, 12)
  return {
    x: originX,
    y: originY,
    velocityX: Math.cos(angleRad) * speed,
    velocityY: Math.sin(angleRad) * speed,
    rotationRad: randomBetween(0, Math.PI * 2),
    rotationSpeedRad: randomBetween(-0.24, 0.24),
    tumblePhaseRad: randomBetween(0, Math.PI * 2),
    tumbleSpeedRad: randomBetween(0.14, 0.3),
    wobblePhaseRad: randomBetween(0, Math.PI * 2),
    wobbleSpeedRad: randomBetween(0.08, 0.16),
    wobbleAmplitude: shape === 'strip' ? randomBetween(1, 1.8) : randomBetween(0.3, 0.9),
    width,
    height,
    shape,
    color: palette[Math.floor(Math.random() * palette.length)] ?? '#1d1a14',
    ageMs: 0,
    lifetimeMs: randomBetween(1400, 2600),
  }
}

/**
 * Size the canvas bitmap to the viewport (capped-DPR aware) when it drifted.
 * Called every frame: it self-heals the initial fire racing the teleport
 * patch, and follows window resizes for free.
 * @param canvas - The burst canvas.
 */
function ensureCanvasSized(canvas: HTMLCanvasElement): void {
  const pixelRatio: number = Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO)
  const width: number = Math.floor(window.innerWidth * pixelRatio)
  const height: number = Math.floor(window.innerHeight * pixelRatio)
  if (canvas.width === width && canvas.height === height) return
  canvas.width = width
  canvas.height = height
  canvas.getContext('2d')?.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
}

/**
 * Advance and draw every particle, then schedule the next frame while any
 * particle or pending wave remains.
 * @param frameMs - High-resolution timestamp of the frame.
 */
function renderFrame(frameMs: number): void {
  const canvas: HTMLCanvasElement | null = canvasElement.value
  const context: CanvasRenderingContext2D | null = canvas?.getContext('2d') ?? null
  if (!canvas || !context) {
    // Le patch du teleport n'a pas encore posé le canvas : on réessaie au frame suivant.
    frameHandle = requestAnimationFrame(renderFrame)
    return
  }
  ensureCanvasSized(canvas)
  const elapsedMs: number = previousFrameMs === 0 ? 16.7 : Math.min(frameMs - previousFrameMs, 48)
  previousFrameMs = frameMs
  const step: number = elapsedMs / (1000 / 60)
  context.clearRect(0, 0, window.innerWidth, window.innerHeight)

  const alive: CelebrationParticle[] = []
  particles.forEach((particle: CelebrationParticle): void => {
    particle.ageMs += elapsedMs
    if (particle.ageMs >= particle.lifetimeMs || particle.y > window.innerHeight + 40) return
    particle.velocityY += GRAVITY_PER_STEP * step
    particle.velocityX *= AIR_DRAG_PER_STEP
    particle.velocityY *= AIR_DRAG_PER_STEP
    particle.wobblePhaseRad += particle.wobbleSpeedRad * step
    particle.x += particle.velocityX * step + Math.sin(particle.wobblePhaseRad) * particle.wobbleAmplitude * step
    particle.y += particle.velocityY * step
    particle.rotationRad += particle.rotationSpeedRad * step
    particle.tumblePhaseRad += particle.tumbleSpeedRad * step

    const lifeRatio: number = particle.ageMs / particle.lifetimeMs
    const opacity: number =
      lifeRatio < FADE_START_LIFE_RATIO ? 1 : 1 - (lifeRatio - FADE_START_LIFE_RATIO) / (1 - FADE_START_LIFE_RATIO)
    context.save()
    context.translate(particle.x, particle.y)
    context.rotate(particle.rotationRad)
    // scaleY oscillant : illusion de retournement 3D d'un bout de papier.
    if (particle.shape !== 'dot') context.scale(1, Math.max(Math.abs(Math.sin(particle.tumblePhaseRad)), 0.15))
    context.globalAlpha = opacity
    context.fillStyle = particle.color
    if (particle.shape === 'dot') {
      context.beginPath()
      context.arc(0, 0, particle.width / 2, 0, Math.PI * 2)
      context.fill()
    } else {
      context.fillRect(-particle.width / 2, -particle.height / 2, particle.width, particle.height)
    }
    context.restore()
    alive.push(particle)
  })
  particles = alive

  if (particles.length === 0 && waveTimers.length === 0) {
    stopSimulation()
    return
  }
  frameHandle = requestAnimationFrame(renderFrame)
}

/** Halt the frame loop and hide the canvas. */
function stopSimulation(): void {
  if (frameHandle !== null) cancelAnimationFrame(frameHandle)
  frameHandle = null
  previousFrameMs = 0
  particles = []
  isRunning.value = false
}

/** Fire the burst: schedule every wave then start the frame loop. */
function fire(): void {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const palette: string[] = resolvePalette()
  const origin: CelebrationBurstOrigin = resolveOrigin()
  isRunning.value = true
  waveTimers = BURST_WAVES.map((wave: CelebrationBurstWave): ReturnType<typeof setTimeout> => {
    const timer: ReturnType<typeof setTimeout> = setTimeout((): void => {
      waveTimers = waveTimers.filter((pending: ReturnType<typeof setTimeout>): boolean => pending !== timer)
      for (let index: number = 0; index < wave.particleCount; index += 1) {
        particles.push(spawnParticle(origin.x, origin.y, wave, palette))
      }
    }, wave.delayMs)
    return timer
  })
  if (frameHandle === null) frameHandle = requestAnimationFrame(renderFrame)
}

watch(
  (): boolean => props.active,
  (isActive: boolean): void => {
    if (isActive && isMounted.value) fire()
  },
)

onMounted((): void => {
  isMounted.value = true
  if (props.active) fire()
})

onBeforeUnmount((): void => {
  waveTimers.forEach((timer: ReturnType<typeof setTimeout>): void => clearTimeout(timer))
  waveTimers = []
  stopSimulation()
})
</script>
