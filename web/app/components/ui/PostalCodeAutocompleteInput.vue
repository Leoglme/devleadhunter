<template>
  <div class="relative w-full">
    <input
      :id="inputId"
      :value="modelValue"
      type="text"
      inputmode="numeric"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      autocomplete="postal-code"
      role="combobox"
      :aria-expanded="isOpen"
      class="input-field"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
      @keydown="handleKeydown"
    />

    <ul v-if="isOpen" class="input-autocomplete-menu input-autocomplete-menu--wide">
      <li v-if="isSearching" class="flex items-center gap-2 px-3 py-2 text-sm text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
        Recherche…
      </li>
      <li v-else-if="suggestions.length === 0" class="px-3 py-2 text-sm text-[var(--app-ink-soft)]">
        Aucune ville trouvée pour ce code postal
      </li>
      <template v-else>
        <li
          v-for="(suggestion, index) in suggestions"
          :key="`${modelValue}-${suggestion.nom}`"
          :class="[
            'flex cursor-pointer items-center gap-3 px-3 py-2 text-sm text-[var(--app-ink)]',
            index === activeIndex ? 'bg-[var(--app-surface-2)]' : 'hover:bg-[var(--app-surface-2)]',
          ]"
          @mousedown.prevent="selectSuggestion(suggestion)"
          @mousemove="activeIndex = index"
        >
          <span class="min-w-0 flex-1 leading-snug font-medium">{{ suggestion.nom }}</span>
          <span class="shrink-0 text-xs text-[var(--app-ink-soft)] tabular-nums">{{ modelValue }}</span>
        </li>
      </template>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { UseDebounceFnReturn } from '@vueuse/core'
import type { UiPostalCodeAutocompleteInputEmits } from '~/types/UiPostalCodeAutocompleteInput'
import type { EmitFn, Ref } from 'vue'
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import type { PostalCodeAutocompleteInputProps, PostalCodeCitySuggestion } from '~/types/PostalCodeAutocompleteInput'
import { POSTAL_CODE_LOOKUP_LENGTH, searchCitiesByPostalCode } from '~/services/franceGeoAutocompleteService'

const debounceDelayMs: number = 300
const blurCloseDelayMs: number = 150

/** Postal code field with commune lookup to prefill the matching city. */
const props: PostalCodeAutocompleteInputProps = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  placeholder: {
    type: String,
    default: '35000',
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

const emit: EmitFn<UiPostalCodeAutocompleteInputEmits> = defineEmits<UiPostalCodeAutocompleteInputEmits>()

const suggestions: Ref<PostalCodeCitySuggestion[]> = ref([])
const isSearching: Ref<boolean> = ref(false)
const isOpen: Ref<boolean> = ref(false)
const activeIndex: Ref<number> = ref(-1)
let searchRequestId: number = 0
let blurTimeoutId: ReturnType<typeof setTimeout> | null = null

/**
 * Fetch communes for a complete five-digit postal code.
 * @param postalCode - Digits typed by the user.
 * @returns A promise resolved once suggestions are updated.
 */
const fetchSuggestions: UseDebounceFnReturn<(postalCode: string) => Promise<void>> = useDebounceFn(
  async (postalCode: string): Promise<void> => {
    const trimmedCode: string = postalCode.trim()
    if (trimmedCode.length < POSTAL_CODE_LOOKUP_LENGTH) {
      suggestions.value = []
      isOpen.value = false
      return
    }

    const requestId: number = ++searchRequestId
    isSearching.value = true
    isOpen.value = true

    try {
      const results: PostalCodeCitySuggestion[] = await searchCitiesByPostalCode(trimmedCode)
      if (requestId !== searchRequestId) {
        return
      }
      suggestions.value = results
      if (results.length === 1) {
        selectSuggestion(results[0] as PostalCodeCitySuggestion)
      }
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
 * Keep only digits in the postal code and trigger a lookup once five digits are present.
 * @param event - Native input event.
 */
function handleInput(event: Event): void {
  if (props.disabled) {
    return
  }
  const rawValue: string = (event.target as HTMLInputElement).value
  const digitsOnly: string = rawValue.replace(/\D/g, '').slice(0, POSTAL_CODE_LOOKUP_LENGTH)
  emit('update:modelValue', digitsOnly)

  if (digitsOnly.length === POSTAL_CODE_LOOKUP_LENGTH) {
    isSearching.value = true
    isOpen.value = true
    void fetchSuggestions(digitsOnly)
    return
  }

  suggestions.value = []
  isSearching.value = false
  isOpen.value = false
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
  if (props.modelValue.trim().length === POSTAL_CODE_LOOKUP_LENGTH && suggestions.value.length > 1) {
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
    const suggestion: PostalCodeCitySuggestion | undefined = suggestions.value[activeIndex.value]
    if (suggestion) {
      selectSuggestion(suggestion)
    }
  } else if (event.key === 'Escape') {
    isOpen.value = false
  }
}

/**
 * Notify the parent of the commune linked to the postal code.
 * @param suggestion - Commune picked (or auto-selected when unique).
 */
function selectSuggestion(suggestion: PostalCodeCitySuggestion): void {
  emit('select', suggestion)
  isOpen.value = false
  activeIndex.value = -1
}
</script>
