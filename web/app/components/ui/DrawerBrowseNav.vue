<template>
  <div
    v-if="props.positionLabel"
    class="flex items-center justify-between gap-3 border-b border-[var(--app-line-soft)] px-5 py-2.5"
  >
    <button
      type="button"
      class="app-btn-secondary h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-40"
      :disabled="!canPrevious"
      @click="emit('previous')"
    >
      <UIcon name="i-lucide-chevron-left" class="h-3.5 w-3.5" />
      Précédent
    </button>
    <span class="font-label text-[11px] whitespace-nowrap text-[var(--app-ink-soft)] tabular-nums">
      {{ positionLabel }}
    </span>
    <button
      type="button"
      class="app-btn-secondary h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-40"
      :disabled="!canNext"
      @click="emit('next')"
    >
      Suivant
      <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5" />
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { UiDrawerBrowseNavProps } from '~/types/UiDrawerBrowseNav'

/**
 * Step-through strip displayed under a drawer header, so the drawer can walk the
 * list its calling page shows without closing. Renders nothing while
 * `positionLabel` is empty — that is how a caller says « this list is unknown ».
 */
const props: UiDrawerBrowseNavProps = defineProps({
  /** Human position in the browsed list, e.g. « 3 / 42 ». Empty hides the strip. */
  positionLabel: {
    type: String,
    default: '',
  },
  /** Whether a previous entry exists in the browsed list. */
  canPrevious: {
    type: Boolean,
    default: false,
  },
  /** Whether a next entry exists in the browsed list. */
  canNext: {
    type: Boolean,
    default: false,
  },
})

const emit: {
  (e: 'previous' | 'next'): void
} = defineEmits<{
  (e: 'previous' | 'next'): void
}>()
</script>
