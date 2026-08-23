<template>
  <span
    v-if="config"
    class="inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[10px] font-semibold"
    :style="config.style"
  >
    {{ config.label }}
  </span>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { TemperaturePresentation, UiTemperatureBadgeProps } from '~/types/UiTemperatureBadge'

const props: UiTemperatureBadgeProps = defineProps({
  temperature: {
    type: String as PropType<string>,
    required: true,
  },
})

const TEMPERATURE_CONFIG: Record<string, TemperaturePresentation> = {
  hot: { label: 'Chaud', style: { color: 'var(--app-red)', backgroundColor: 'var(--app-red-soft)' } },
  warm: { label: 'Tiède', style: { color: 'var(--app-accent-ink)', backgroundColor: 'var(--app-accent-soft)' } },
  cold: { label: 'Froid', style: { color: 'var(--app-blue)', backgroundColor: 'var(--app-blue-soft)' } },
}

const config: ComputedRef<TemperaturePresentation | null> = computed(
  (): TemperaturePresentation | null => TEMPERATURE_CONFIG[props.temperature] ?? null,
)
</script>
