<template>
  <div class="app-theme" :data-theme="theme">
    <div
      class="flex min-h-dvh flex-col items-center justify-center px-6 py-16 text-center"
      :style="{ backgroundColor: 'var(--app-bg)' }"
    >
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />

      <p class="app-label mt-6">Erreur {{ statusCode }}</p>
      <h1 class="app-page-title mt-2 text-2xl sm:text-3xl">{{ title }}</h1>
      <p class="mt-3 max-w-md text-sm leading-relaxed text-[var(--app-ink-soft)]">{{ description }}</p>

      <div class="mt-8 flex flex-wrap items-center justify-center gap-3">
        <button v-if="isNotFound" type="button" class="app-btn-primary" @click="goHome">
          <UIcon name="i-lucide-layout-dashboard" class="h-3.5 w-3.5" />
          Retour au tableau de bord
        </button>
        <button v-else type="button" class="app-btn-primary" @click="retry">
          <UIcon name="i-lucide-rotate-cw" class="h-3.5 w-3.5" />
          Réessayer
        </button>
        <button v-if="!isNotFound" type="button" class="app-btn-secondary" @click="goHome">
          Retour au tableau de bord
        </button>
      </div>

      <p v-if="errorMessage" class="mt-8 max-w-lg font-mono text-xs break-words text-[var(--app-faint)]">
        {{ errorMessage }}
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { NuxtError } from '#app'
import type { AppTheme } from '~/types/AppTheme'
import type { ErrorPageProps } from '~/types/ErrorPage'
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, onMounted } from 'vue'
import { useAppTheme } from '~/composables/useAppTheme'

/** Application-wide error screen, replacing the default Nuxt page. */
const props: ErrorPageProps = defineProps({
  error: {
    type: Object as PropType<NuxtError>,
    required: true,
  },
})

const { theme, initTheme }: { theme: Ref<AppTheme, AppTheme>; initTheme: () => void; toggleTheme: () => void } =
  useAppTheme()

const route: ReturnType<typeof useRoute> = useRoute()

const statusCode: ComputedRef<number> = computed((): number => props.error.statusCode ?? 500)

const isNotFound: ComputedRef<boolean> = computed((): boolean => statusCode.value === 404)

const title: ComputedRef<string> = computed((): string =>
  isNotFound.value ? 'Page introuvable' : 'Un problème est survenu',
)

const description: ComputedRef<string> = computed((): string =>
  isNotFound.value
    ? "Cette page n'existe pas ou a été déplacée. Le lien que vous avez suivi est peut-être périmé."
    : "L'application n'a pas réussi à afficher cette page. Réessayez — si ça persiste, ouvrez un ticket au support.",
)

/** Technical detail, useful when reporting the error; never shown for a plain 404. */
const errorMessage: ComputedRef<string> = computed((): string => (isNotFound.value ? '' : (props.error.message ?? '')))

/** Leave the error state and go back to the dashboard. */
function goHome(): void {
  void clearError({ redirect: '/dashboard' })
}

/** Retry the route that failed. */
function retry(): void {
  void clearError({ redirect: route.fullPath })
}

onMounted((): void => {
  initTheme()
})
</script>
