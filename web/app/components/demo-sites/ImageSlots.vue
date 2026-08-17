<template>
  <div class="space-y-4">
    <div>
      <h3 class="text-sm font-semibold text-[var(--app-ink)]">Images du site</h3>
      <p class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        La 1ʳᵉ photo devient l'en-tête, la 2ᵉ la section « à propos », le reste la galerie. Glissez la poignée ou
        utilisez les flèches pour changer, puis régénérez pour publier.
      </p>
    </div>

    <ul v-if="used.length" class="space-y-2" aria-label="Photos placées sur le site">
      <li
        v-for="(url, i) in used"
        :key="url"
        :class="[
          'flex items-center gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-2 transition-opacity',
          dragIndex === i ? 'opacity-50' : 'opacity-100',
        ]"
        @dragover.prevent
        @drop.prevent="onDrop(i)"
      >
        <button
          type="button"
          class="cursor-grab text-[var(--app-ink-soft)] active:cursor-grabbing"
          aria-label="Déplacer la photo"
          draggable="true"
          @dragstart="onDragStart(i)"
          @dragend="onDragEnd"
        >
          <UIcon name="i-lucide-grip-vertical" class="h-4 w-4" />
        </button>

        <img :src="url" :alt="`Photo ${i + 1}`" class="h-14 w-20 shrink-0 rounded-lg object-cover" draggable="false" />

        <span :class="['rounded-full px-2 py-0.5 text-[10px] font-bold uppercase', slotBadgeClass(i)]">
          {{ slotLabel(i) }}
        </span>

        <div class="ml-auto flex items-center gap-1">
          <button
            type="button"
            class="rounded-md p-1.5 text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:opacity-30"
            aria-label="Mettre en photo principale"
            :disabled="i === 0"
            @click="moveToFront(i)"
          >
            <UIcon name="i-lucide-chevrons-up" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="rounded-md p-1.5 text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:opacity-30"
            aria-label="Monter"
            :disabled="i === 0"
            @click="move(i, i - 1)"
          >
            <UIcon name="i-lucide-arrow-up" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="rounded-md p-1.5 text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:opacity-30"
            aria-label="Descendre"
            :disabled="i === used.length - 1"
            @click="move(i, i + 1)"
          >
            <UIcon name="i-lucide-arrow-down" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="rounded-md p-1.5 text-[var(--app-ink-soft)] hover:text-[var(--app-red)]"
            aria-label="Retirer du site"
            @click="removeAt(i)"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
      </li>
    </ul>

    <p v-else class="rounded-xl border border-dashed border-[var(--app-line)] p-4 text-xs text-[var(--app-ink-soft)]">
      Aucune photo placée : le site utilise ses images par défaut. Ajoutez-en depuis « Non utilisées ».
    </p>

    <div v-if="unused.length" class="space-y-2 border-t border-[var(--app-line)] pt-4">
      <p class="text-xs font-semibold text-[var(--app-ink-soft)]">Non utilisées ({{ unused.length }})</p>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="url in unused"
          :key="url"
          type="button"
          class="group relative overflow-hidden rounded-lg border border-[var(--app-line)]"
          title="Ajouter au site"
          @click="add(url)"
        >
          <img
            :src="url"
            alt="Photo non utilisée"
            class="h-16 w-24 object-cover opacity-70 transition-opacity group-hover:opacity-100"
            draggable="false"
          />
          <span
            class="absolute inset-0 flex items-center justify-center bg-black/40 text-white opacity-0 transition-opacity group-hover:opacity-100"
          >
            <UIcon name="i-lucide-plus" class="h-5 w-5" />
          </span>
        </button>
      </div>
    </div>

    <div
      v-if="hasPendingChanges"
      class="flex flex-col gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] px-4 py-3.5 @2xl:flex-row @2xl:items-center @2xl:justify-between"
    >
      <p class="flex items-start gap-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
        Ce nouvel ordre n'est pas encore en ligne : régénérez pour publier le rendu.
      </p>
      <div class="flex shrink-0 gap-2">
        <button type="button" class="btn-secondary text-xs" :disabled="busy" @click="reset">Annuler</button>
        <button type="button" class="btn-primary text-xs" :disabled="busy" @click="apply">
          {{ busy ? 'Régénération…' : 'Appliquer & régénérer' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'

/** ``order`` = current placement (hero/about/gallery); ``pool`` = every usable photo. */
type ImageSlotsProps = {
  pool: string[]
  order: string[]
  busy: boolean
}

type ImageSlotsEmits = {
  apply: [order: string[]]
}

/** Editor placing the prospect's photos into the site's hero / about / gallery slots. */
const props: ImageSlotsProps = defineProps({
  pool: {
    type: Array as PropType<string[]>,
    required: true,
  },
  order: {
    type: Array as PropType<string[]>,
    required: true,
  },
  busy: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<ImageSlotsEmits> = defineEmits<ImageSlotsEmits>()

const used: Ref<string[]> = ref([...props.order])
const dragIndex: Ref<number | null> = ref(null)

const unused: ComputedRef<string[]> = computed((): string[] =>
  props.pool.filter((url: string): boolean => !used.value.includes(url)),
)

const hasPendingChanges: ComputedRef<boolean> = computed(
  (): boolean => used.value.join('\n') !== props.order.join('\n'),
)

/**
 * Destination label for a photo at a given placement index.
 * @param index - Position in the used list.
 */
function slotLabel(index: number): string {
  if (index === 0) return 'Principale'
  if (index === 1) return 'À propos'
  return `Galerie ${index - 1}`
}

/**
 * Badge colour for a placement slot — the hero slot is highlighted, the rest are muted.
 * @param index - Position in the used list.
 */
function slotBadgeClass(index: number): string {
  if (index === 0) return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
  return 'bg-[var(--app-line)] text-[var(--app-ink-soft)]'
}

/**
 * Move a used photo from one index to another, keeping the rest in order.
 * @param from - Current index.
 * @param to - Target index.
 */
function move(from: number, to: number): void {
  if (to < 0 || to >= used.value.length) return
  const next: string[] = [...used.value]
  const moved: string | undefined = next.splice(from, 1)[0]
  if (moved === undefined) return
  next.splice(to, 0, moved)
  used.value = next
}

/**
 * Promote a used photo to the hero slot (index 0).
 * @param index - Current index of the photo.
 */
function moveToFront(index: number): void {
  move(index, 0)
}

/**
 * Remove a photo from the site (it returns to the "unused" pool).
 * @param index - Index of the photo to drop.
 */
function removeAt(index: number): void {
  used.value = used.value.filter((_: string, i: number): boolean => i !== index)
}

/**
 * Add an unused photo to the end of the placement (gallery).
 * @param url - Photo URL to add.
 */
function add(url: string): void {
  if (used.value.includes(url)) return
  used.value = [...used.value, url]
}

/**
 * Start dragging a used photo.
 * @param index - Index being dragged.
 */
function onDragStart(index: number): void {
  dragIndex.value = index
}

/**
 * Reorder the dragged photo onto the drop target row.
 * @param index - Drop target index.
 */
function onDrop(index: number): void {
  if (dragIndex.value !== null && dragIndex.value !== index) {
    move(dragIndex.value, index)
  }
  dragIndex.value = null
}

/** Clear the drag state when the drag ends anywhere. */
function onDragEnd(): void {
  dragIndex.value = null
}

/** Revert the local placement to the published order. */
function reset(): void {
  used.value = [...props.order]
}

/** Emit the curated placement for the parent to persist and regenerate. */
function apply(): void {
  emit('apply', [...used.value])
}

watch(
  (): string[] => props.order,
  (order: string[]): void => {
    used.value = [...order]
  },
)
</script>
