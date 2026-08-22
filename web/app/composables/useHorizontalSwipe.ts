import type { MaybeRefOrGetter, Ref } from 'vue'
import { toValue } from 'vue'
import type { Position, UseSwipeDirection } from '@vueuse/core'
import { useSwipe } from '@vueuse/core'
import type { HorizontalSwipeOptions, UseHorizontalSwipeReturn } from '~/types/Composables'

/** Form fields (and explicit opt-out zones) whose horizontal drag is selection/reorder, never a swipe. */
const IGNORED_SWIPE_ORIGIN_SELECTOR: string = 'input, textarea, select, [contenteditable="true"], [data-swipe-ignore]'

/** Minimum horizontal travel (px) before a drag is treated as a swipe. */
const DEFAULT_SWIPE_THRESHOLD_PX: number = 60

/**
 * Horizontal swipe gesture with an optional left-edge guard and origin opt-outs.
 * @param target - Element (or ref/getter) the gesture listens on.
 * @param options - Callbacks and guards; see `HorizontalSwipeOptions`.
 * @returns The reactive `isSwiping` flag.
 */
export function useHorizontalSwipe(
  target: MaybeRefOrGetter<EventTarget | null | undefined>,
  options: HorizontalSwipeOptions,
): UseHorizontalSwipeReturn {
  const ignoreSelector: string = options.ignoreSelector ?? IGNORED_SWIPE_ORIGIN_SELECTOR

  // Resolved at swipe start, honoured at swipe end: a disabled gesture or one born in an opt-out zone is dropped.
  let isGestureDropped: boolean = false

  const { isSwiping, coordsStart }: { isSwiping: Ref<boolean>; coordsStart: Readonly<Position> } = useSwipe(target, {
    threshold: options.threshold ?? DEFAULT_SWIPE_THRESHOLD_PX,
    passive: true,
    /**
     * Capture the gesture origin, dropping it when disabled or born in an opt-out zone.
     * @param event - Native touch-start event.
     */
    onSwipeStart(event: TouchEvent): void {
      isGestureDropped = toValue(options.enabled ?? true) === false
      if (isGestureDropped) return
      const origin: HTMLElement | null = event.target instanceof HTMLElement ? event.target : null
      if (origin?.closest(ignoreSelector)) {
        isGestureDropped = true
      }
    },
    /**
     * Fire the matching horizontal callback once a kept swipe settles.
     * @param _event - Native touch-end event (unused).
     * @param direction - Dominant direction elected by VueUse.
     */
    onSwipeEnd(_event: TouchEvent, direction: UseSwipeDirection): void {
      if (isGestureDropped) return
      if (options.edgeStartPx !== undefined && coordsStart.x > options.edgeStartPx) return
      if (direction === 'right') {
        options.onSwipeRight?.()
      } else if (direction === 'left') {
        options.onSwipeLeft?.()
      }
    },
  })

  return { isSwiping }
}
