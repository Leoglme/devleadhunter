<template>
  <div class="relative w-full">
    <input
      :id="inputId"
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      autocomplete="off"
      role="combobox"
      :aria-expanded="isOpen"
      class="input-field"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
      @keydown="handleKeydown"
    />

    <ul
      v-if="isOpen"
      class="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] shadow-lg"
    >
      <li v-if="isSearching" class="flex items-center gap-2 px-3 py-2 text-sm text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
        Recherche…
      </li>
      <li v-else-if="suggestions.length === 0" class="px-3 py-2 text-sm text-[var(--app-ink-soft)]">
        Aucune adresse trouvée
      </li>
      <template v-else>
        <li
          v-for="(suggestion, index) in suggestions"
          :key="`${suggestion.postcode}-${suggestion.label}`"
          :class="[
            'cursor-pointer px-3 py-2 text-sm text-[var(--app-ink)]',
            index === activeIndex ? 'bg-[var(--app-surface-2)]' : 'hover:bg-[var(--app-surface-2)]',
          ]"
          @mousedown.prevent="selectSuggestion(suggestion)"
          @mousemove="activeIndex = index"
        >
          <span class="font-medium">{{ suggestion.label }}</span>
        </li>
      </template>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { UseDebounceFnReturn } from '@vueuse/core'
import type { UiAddressAutocompleteInputEmits } from '~/types/UiAddressAutocompleteInput'
import type { EmitFn, Ref } from 'vue'
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import type { AddressAutocompleteInputProps, AddressSuggestion } from '~/types/AddressAutocompleteInput'
import { searchAddressSuggestions } from '~/services/franceGeoAutocompleteService'

const minQueryLength: number = 2
const debounceDelayMs: number = 300
const blurCloseDelayMs: number = 150

/** Street address autocomplete backed by the Base Adresse Nationale (BAN). */
const props: AddressAutocompleteInputProps = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  placeholder: {
    type: String,
    default: '12 rue de la Paix',
  },
  inputId: {
    type: String,
    default: undefined,
  },
  required: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiAddressAutocompleteInputEmits> = defineEmits<UiAddressAutocompleteInputEmits>()

const suggestions: Ref<AddressSuggestion[]> = ref([])
const isSearching: Ref<boolean> = ref(false)
const isOpen: Ref<boolean> = ref(false)
const activeIndex: Ref<number> = ref(-1)
let searchRequestId: number = 0
let blurTimeoutId: ReturnType<typeof setTimeout> | null = null

/**
 * Fetch BAN suggestions for the current query.
 * @param query - Partial address typed by the user.
 * @returns A promise resolved once suggestions are updated.
 */
const fetchSuggestions: UseDebounceFnReturn<(query: string) => Promise<void>> = useDebounceFn(
  async (query: string): Promise<void> => {
    const trimmedQuery: string = query.trim()
    if (trimmedQuery.length < minQueryLength) {
      suggestions.value = []
      isOpen.value = false
      return
    }

    const requestId: number = ++searchRequestId
    isSearching.value = true
    isOpen.value = true

    try {
      const results: AddressSuggestion[] = await searchAddressSuggestions(trimmedQuery)
      if (requestId !== searchRequestId) {
        return
      }
      suggestions.value = results
    } catch {
      if (requestId !== searchRequestId) {
        return
      }
      suggestions.value = []
    } finally {
      if (requestId === searchRequestId) {
        isSearching.value = false
        activeIndex.value = -1
      }
    }
  },
  debounceDelayMs,
)

/**
 * Propagate typing to the v-model and trigger a debounced BAN lookup.
 * @param event - Native input event.
 */
function handleInput(event: Event): void {
  if (props.disabled) {
    return
  }
  const value: string = (event.target as HTMLInputElement).value
  emit('update:modelValue', value)
  if (value.trim().length >= minQueryLength) {
    isSearching.value = true
    isOpen.value = true
  } else {
    suggestions.value = []
    isSearching.value = false
    isOpen.value = false
  }
  void fetchSuggestions(value)
}

/**
 * Reopen the dropdown when the field regains focus.
 */
function handleFocus(): void {
  if (props.disabled) {
    return
  }
  if (blurTimeoutId !== null) {
    clearTimeout(blurTimeoutId)
    blurTimeoutId = null
  }
  if (props.modelValue.trim().length >= minQueryLength && suggestions.value.length > 0) {
    isOpen.value = true
  }
}

/**
 * Close the dropdown after a short delay so mousedown on a suggestion can fire.
 */
function handleBlur(): void {
  blurTimeoutId = setTimeout((): void => {
    isOpen.value = false
    blurTimeoutId = null
  }, blurCloseDelayMs)
}

/**
 * Keyboard navigation inside the suggestion list.
 * @param event - Native keydown event.
 */
function handleKeydown(event: KeyboardEvent): void {
  if (!isOpen.value || suggestions.value.length === 0) {
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = activeIndex.value <= 0 ? suggestions.value.length - 1 : activeIndex.value - 1
  } else if (event.key === 'Enter' && activeIndex.value >= 0) {
    event.preventDefault()
    const suggestion: AddressSuggestion | undefined = suggestions.value[activeIndex.value]
    if (suggestion) {
      selectSuggestion(suggestion)
    }
  } else if (event.key === 'Escape') {
    isOpen.value = false
  }
}

/**
 * Apply the selected BAN suggestion to the field and notify the parent.
 * @param suggestion - Address picked in the dropdown.
 */
function selectSuggestion(suggestion: AddressSuggestion): void {
  emit('update:modelValue', suggestion.name)
  emit('select', suggestion)
  isOpen.value = false
  activeIndex.value = -1
}
</script>
