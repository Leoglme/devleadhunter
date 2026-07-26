<template>
  <div class="@container">
    <div class="rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4 md:hidden">
      <div class="flex items-center gap-1.5">
        <span
          v-for="step in steps"
          :key="step.id"
          class="h-1 flex-1 rounded-full transition-colors"
          :class="segmentClass(step.id)"
        />
      </div>
      <p class="app-label mt-3">Étape {{ modelValue }} sur {{ steps.length }}</p>
      <p class="mt-1 text-base leading-snug font-semibold text-[var(--app-ink)]">{{ activeStep?.label }}</p>
      <p v-if="activeStep?.hint" class="mt-0.5 text-xs leading-snug text-[var(--app-ink-soft)]">
        {{ activeStep.hint }}
      </p>
    </div>

    <ol
      class="hidden rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-2 md:flex md:items-center md:gap-2"
      aria-label="Progression"
    >
      <li
        v-for="(step, index) in steps"
        :key="step.id"
        class="flex min-w-0 items-center gap-2"
        :class="index > 0 && 'flex-1'"
      >
        <span
          v-if="index > 0"
          aria-hidden="true"
          class="h-px min-w-4 flex-1 rounded-full transition-colors"
          :class="connectorClass(step.id - 1)"
        />
        <button
          type="button"
          :disabled="step.id >= modelValue"
          :aria-current="step.id === modelValue ? 'step' : undefined"
          class="flex shrink-0 items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-left transition-colors"
          :class="
            step.id === modelValue
              ? 'bg-[var(--app-surface-2)]'
              : step.id < modelValue
                ? 'cursor-pointer hover:bg-[var(--app-surface-2)]/60'
                : 'cursor-default'
          "
          @click="handleStepNavigate(step.id)"
        >
          <span
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors"
            :class="stepNodeClass(step.id)"
          >
            <UiStepCheck v-if="step.id < modelValue" class="h-4 w-4" />
            <template v-else>{{ step.id }}</template>
          </span>
          <span class="min-w-0">
            <span
              class="block text-[13px] leading-snug font-semibold"
              :class="step.id === modelValue ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)]'"
            >
              {{ step.label }}
            </span>
            <span v-if="step.hint" class="mt-0.5 hidden text-[11px] leading-snug text-[var(--app-faint)] @3xl:block">
              {{ step.hint }}
            </span>
          </span>
        </button>
      </li>
    </ol>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import { computed } from 'vue'
import type { UiWizardStep, UiWizardStepperEmits, UiWizardStepperProps } from '~/types/UiWizardStepper'

/** Multi-step wizard stepper; compact indicator on mobile. */
const props: UiWizardStepperProps = defineProps({
  steps: {
    type: Array as PropType<UiWizardStep[]>,
    required: true,
  },
  modelValue: {
    type: Number,
    required: true,
  },
})

const emit: EmitFn<UiWizardStepperEmits> = defineEmits<UiWizardStepperEmits>()

/** The step currently being shown. */
const activeStep: ComputedRef<UiWizardStep | undefined> = computed((): UiWizardStep | undefined =>
  props.steps.find((step: UiWizardStep): boolean => step.id === props.modelValue),
)

/**
 * Classes for a step node based on its state (done / current / upcoming).
 * @param stepId - The step id (1-based).
 * @returns Border, background and text classes.
 */
function stepNodeClass(stepId: number): string {
  if (stepId < props.modelValue) {
    return 'border-[var(--app-green)] bg-[var(--app-green-soft)] text-[var(--app-green)]'
  }
  if (stepId === props.modelValue) return 'border-[var(--app-ink)] text-[var(--app-ink)]'
  return 'border-[var(--app-line)] text-[var(--app-ink-soft)]'
}

/**
 * Classes for the connector line drawn between a step and the next one.
 * @param stepId - The step the connector starts from (1-based).
 * @returns Background classes for the 1px line.
 */
function connectorClass(stepId: number): string {
  return stepId < props.modelValue ? 'bg-[var(--app-green)]' : 'bg-[var(--app-line)]'
}

/**
 * Classes for a segment of the mobile progress bar. Reached steps (done and
 * current) share one colour so the bar reads as a single progress fill.
 * @param stepId - The step the segment stands for (1-based).
 * @returns Background classes for the segment.
 */
function segmentClass(stepId: number): string {
  return stepId <= props.modelValue ? 'bg-[var(--app-green)]' : 'bg-[var(--app-line)]'
}

/**
 * A step node was clicked — only going back to a completed step is allowed.
 * @param stepId - Target step id.
 */
function handleStepNavigate(stepId: number): void {
  if (stepId < props.modelValue) emit('update:modelValue', stepId)
}
</script>
