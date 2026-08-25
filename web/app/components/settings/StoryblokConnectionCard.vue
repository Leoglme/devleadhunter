<template>
  <section class="card p-5">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-sm font-bold">Connexion Storyblok</h2>
        <p class="text-muted mt-1 text-xs leading-relaxed">
          Permet d'ajouter la séquence « édition du site » (CMS Storyblok) au fond de la vidéo. Réutilise votre session
          navigateur ; sinon, connectez-vous une fois ici.
        </p>
      </div>
      <span :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', badgeClass]">{{ badgeLabel }}</span>
    </div>

    <p v-if="!isDesktop" class="text-muted mt-4 text-xs">
      Disponible uniquement dans l'application desktop (la session vit sur votre machine).
    </p>

    <div v-else class="mt-4 flex items-center gap-3">
      <button
        v-if="session.state === 'needs_login' || session.state === 'busy'"
        type="button"
        class="btn-primary text-xs"
        :disabled="connecting"
        @click="handleConnect"
      >
        {{ connecting ? 'Fenêtre ouverte…' : 'Se connecter à Storyblok' }}
      </button>
      <button type="button" class="btn-secondary text-xs" :disabled="loading" @click="loadState">
        {{ loading ? 'Vérification…' : 'Actualiser' }}
      </button>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { StoryblokSessionInfo } from '~/services/storyblokSidecarService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'

const session: Ref<StoryblokSessionInfo> = ref<StoryblokSessionInfo>({
  state: 'unknown',
  source: null,
  loginWindowOpen: false,
})
const loading: Ref<boolean> = ref<boolean>(false)
const connecting: Ref<boolean> = ref<boolean>(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const isDesktop: ComputedRef<boolean> = computed((): boolean => session.value.state !== 'unknown')

const badgeLabel: ComputedRef<string> = computed((): string => {
  switch (session.value.state) {
    case 'ready':
      return 'Connecté'
    case 'busy':
      return 'Connexion…'
    case 'needs_login':
      return 'À reconnecter'
    default:
      return 'Indisponible'
  }
})

const badgeClass: ComputedRef<string> = computed((): string => {
  if (session.value.state === 'ready') return 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
  if (session.value.state === 'needs_login') return 'bg-[var(--app-red)]/20 text-[var(--app-red)]'
  return 'bg-[var(--app-border)] text-muted'
})

/**
 * Read the current Storyblok session state from the sidecar.
 * @returns {Promise<void>}
 */
async function loadState(): Promise<void> {
  loading.value = true
  try {
    session.value = await StoryblokSidecarService.getSessionState()
  } finally {
    loading.value = false
  }
}

/**
 * Open the one-time login window, then poll until the session is ready.
 * @returns {Promise<void>}
 */
async function handleConnect(): Promise<void> {
  connecting.value = true
  await StoryblokSidecarService.openLogin()
  stopPolling()
  pollTimer = setInterval(async (): Promise<void> => {
    await loadState()
    if (session.value.state === 'ready') stopPolling()
  }, 3000)
}

/**
 * Stop polling the login window.
 * @returns {void}
 */
function stopPolling(): void {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  connecting.value = false
}

onMounted((): void => {
  void loadState()
})

onUnmounted((): void => {
  stopPolling()
})
</script>
