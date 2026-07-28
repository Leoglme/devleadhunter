<template>
  <th
    class="app-label border-b border-[var(--app-line)] px-4 py-2.5"
    :class="[alignClass, srOnly && 'sr-only']"
    v-bind="$attrs"
  >
    <slot />
  </th>
</template>

<script lang="ts" setup>
import type { BaseTableAlign, BaseTableThProps } from '~/types/BaseTable'
import type { ComputedRef } from 'vue'
import { computed } from 'vue'

const props: BaseTableThProps = defineProps({
  align: {
    type: String as () => BaseTableAlign,
    default: 'left',
  },
  srOnly: {
    type: Boolean,
    default: false,
  },
})

const alignClass: ComputedRef<string> = computed((): string => {
  if (props.align === 'center') return 'text-center'
  if (props.align === 'right') return 'text-right'
  return 'text-left'
})
</script>
