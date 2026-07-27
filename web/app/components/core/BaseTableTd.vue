<template>
  <td class="px-4 py-3" :class="alignClass" v-bind="$attrs">
    <slot />
  </td>
</template>

<script lang="ts" setup>
import type { BaseTableAlign, BaseTableTdProps } from '~/types/BaseTable'
import type { ComputedRef } from 'vue'
import { computed } from 'vue'

const props: BaseTableTdProps = defineProps({
  align: {
    type: String as () => BaseTableAlign,
    default: 'left',
  },
})

const alignClass: ComputedRef<string> = computed((): string => {
  if (props.align === 'center') return 'text-center'
  if (props.align === 'right') return 'text-right'
  return 'text-left'
})
</script>
