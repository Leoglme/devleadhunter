<template>
  <div class="celebration-hero relative flex flex-col items-center text-center">
    <UiCelebrationBurst :anchor="badgeElement" :active="isBurstFired" />

    <span
      class="celebration-hero__flash pointer-events-none absolute top-10 h-44 w-44 rounded-full"
      aria-hidden="true"
    />

    <span ref="badgeElement" class="relative flex h-20 w-20 items-center justify-center">
      <svg class="celebration-hero__ring-svg absolute inset-0 h-full w-full" viewBox="0 0 80 80" aria-hidden="true">
        <circle
          class="celebration-hero__ring"
          cx="40"
          cy="40"
          r="36"
          fill="none"
          stroke="var(--app-green)"
          stroke-width="2.5"
          stroke-linecap="round"
        />
      </svg>
      <span class="celebration-hero__halo absolute inset-1 rounded-full" aria-hidden="true" />
      <span
        class="celebration-hero__halo celebration-hero__halo--late absolute inset-1 rounded-full"
        aria-hidden="true"
      />
      <span
        v-for="spark in SPARK_COUNT"
        :key="spark"
        class="celebration-hero__spark absolute h-1.5 w-1.5 rounded-full"
        :style="{ '--spark-angle': `${(360 / SPARK_COUNT) * spark}deg` }"
        aria-hidden="true"
      />
      <span
        class="celebration-hero__badge relative flex h-14 w-14 items-center justify-center rounded-full bg-[var(--app-green-soft)] text-[var(--app-green)]"
      >
        <span class="celebration-hero__icon flex items-center justify-center">
          <UIcon v-if="props.icon" :name="props.icon" class="h-6 w-6" />
          <svg
            v-else
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            class="h-7 w-7"
            aria-hidden="true"
          >
            <path
              class="celebration-hero__check-path"
              d="M4.5 12.5l4.6 4.7L19.5 6.8"
              stroke="currentColor"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
      </span>
    </span>

    <component
      :is="props.headingTag"
      class="font-display mt-5 flex flex-wrap justify-center gap-x-[0.28em] text-2xl font-semibold text-[var(--app-ink)] sm:text-3xl"
    >
      <span
        v-for="(word, index) in titleWords"
        :key="`${word}-${index}`"
        class="celebration-hero__word inline-block"
        :style="{ '--word-order': index }"
      >
        {{ word }}
      </span>
    </component>

    <p
      v-if="props.subtitle"
      class="celebration-hero__subtitle mx-auto mt-2.5 max-w-md text-sm leading-relaxed text-[var(--app-ink-soft)]"
    >
      {{ props.subtitle }}
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CelebrationHeadingTag, UiCelebrationHeroProps } from '~/types/UiCelebrationHero'

/**
 * Celebratory hero closing a completed flow: a success ring draws itself, the
 * icon pops with a spring, sparks and confetti erupt, then the title cascades
 * word by word. Without `icon`, a check mark draws itself inside the badge.
 */
const props: UiCelebrationHeroProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  icon: {
    type: String,
    default: '',
  },
  headingTag: {
    type: String as PropType<CelebrationHeadingTag>,
    default: 'h2',
  },
  celebrate: {
    type: Boolean,
    default: true,
  },
})

/** Sparks projected around the badge when the ring closes. */
const SPARK_COUNT: number = 10

/** Delay before confetti erupts, synced on the ring completing, in ms. */
const BURST_DELAY_MS: number = 600

/** The badge element confetti erupts from. */
const badgeElement: Ref<HTMLElement | null> = ref(null)
/** Whether the confetti burst has been triggered. */
const isBurstFired: Ref<boolean> = ref(false)
/** Timer arming the burst, cleared on unmount. */
const burstTimer: Ref<ReturnType<typeof setTimeout> | null> = ref(null)

/** The title, split for the word-by-word cascade. */
const titleWords: ComputedRef<string[]> = computed((): string[] => props.title.split(' '))

onMounted((): void => {
  if (!props.celebrate) return
  burstTimer.value = setTimeout((): void => {
    isBurstFired.value = true
  }, BURST_DELAY_MS)
})

onBeforeUnmount((): void => {
  if (burstTimer.value !== null) clearTimeout(burstTimer.value)
})
</script>

<style scoped>
/* Chorégraphie : le disque arrive, l'anneau se dessine (0,12 → 0,62 s), puis
   tout éclate d'un coup — icône, flash, halos, étincelles, confettis — avant
   la cascade du titre. */
.celebration-hero__badge {
  animation: celebration-badge-in 0.32s cubic-bezier(0.34, 1.56, 0.64, 1) 0.05s backwards;
}
@keyframes celebration-badge-in {
  from {
    opacity: 0;
    transform: scale(0.5);
  }
}

.celebration-hero__ring-svg {
  transform: rotate(-90deg);
}
.celebration-hero__ring {
  stroke-dasharray: 226.2;
  stroke-dashoffset: 0;
  animation: celebration-ring-draw 0.5s cubic-bezier(0.65, 0, 0.35, 1) 0.12s backwards;
}
@keyframes celebration-ring-draw {
  from {
    stroke-dashoffset: 226.2;
  }
}

.celebration-hero__icon {
  animation: celebration-icon-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.5s backwards;
}
@keyframes celebration-icon-pop {
  from {
    opacity: 0;
    transform: scale(0) rotate(-14deg);
  }
}

.celebration-hero__check-path {
  stroke-dasharray: 26;
  stroke-dashoffset: 0;
  animation: celebration-check-draw 0.3s ease-out 0.62s backwards;
}
@keyframes celebration-check-draw {
  from {
    stroke-dashoffset: 26;
  }
}

.celebration-hero__flash {
  background: radial-gradient(circle, var(--app-accent-soft) 0%, transparent 70%);
  opacity: 0;
  animation: celebration-flash 0.75s ease-out 0.58s;
}
@keyframes celebration-flash {
  0% {
    opacity: 0;
    transform: scale(0.4);
  }
  35% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: scale(1.7);
  }
}

.celebration-hero__halo {
  border: 1.5px solid var(--app-green);
  opacity: 0;
  animation: celebration-halo-out 0.7s cubic-bezier(0.16, 1, 0.3, 1) 0.6s;
}
.celebration-hero__halo--late {
  border-color: var(--app-accent);
  animation-duration: 0.85s;
  animation-delay: 0.78s;
}
@keyframes celebration-halo-out {
  0% {
    opacity: 0.9;
    transform: scale(0.55);
  }
  100% {
    opacity: 0;
    transform: scale(2.4);
  }
}

.celebration-hero__spark {
  top: 50%;
  left: 50%;
  margin: -3px 0 0 -3px;
  background-color: var(--app-green);
  opacity: 0;
  animation: celebration-spark-out 0.65s cubic-bezier(0.16, 1, 0.3, 1) 0.62s;
}
.celebration-hero__spark:nth-of-type(3n) {
  background-color: var(--app-accent);
}
.celebration-hero__spark:nth-of-type(3n + 2) {
  background-color: var(--app-ink);
}
.celebration-hero__spark:nth-of-type(even) {
  height: 4px;
  width: 4px;
  margin: -2px 0 0 -2px;
  animation-delay: 0.7s;
  --spark-distance: -44px;
}
@keyframes celebration-spark-out {
  0% {
    opacity: 0;
    transform: rotate(var(--spark-angle)) translateY(0) scale(0.4);
  }
  30% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: rotate(var(--spark-angle)) translateY(var(--spark-distance, -58px)) scale(0.9);
  }
}

.celebration-hero__word {
  animation: celebration-word-rise 0.45s cubic-bezier(0.16, 1, 0.3, 1) backwards;
  animation-delay: calc(0.7s + var(--word-order) * 70ms);
}
@keyframes celebration-word-rise {
  from {
    opacity: 0;
    transform: translateY(14px);
    filter: blur(4px);
  }
}

.celebration-hero__subtitle {
  animation: celebration-word-rise 0.45s cubic-bezier(0.16, 1, 0.3, 1) 0.98s backwards;
}

@media (prefers-reduced-motion: reduce) {
  .celebration-hero__badge,
  .celebration-hero__ring,
  .celebration-hero__icon,
  .celebration-hero__check-path,
  .celebration-hero__word,
  .celebration-hero__subtitle {
    animation: none;
  }
  .celebration-hero__flash,
  .celebration-hero__halo,
  .celebration-hero__spark {
    display: none;
  }
}
</style>
