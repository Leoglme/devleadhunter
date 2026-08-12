<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="visible"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-[var(--app-overlay)] p-4 backdrop-blur-sm"
      @click.self="closePanel"
    >
      <div class="app-card w-full max-w-lg p-6 shadow-[var(--app-shadow-soft)] sm:p-8">
        <div class="space-y-6">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0 space-y-2">
              <p class="app-label text-[var(--app-accent-ink)]">Mise à jour</p>
              <h2 class="text-xl font-semibold text-[var(--app-ink)] sm:text-2xl">{{ statusTitle }}</h2>
              <p class="text-sm leading-relaxed text-[var(--app-ink-soft)]">{{ statusDescription }}</p>
            </div>
            <div v-if="currentVersion || nextVersion" class="flex shrink-0 flex-wrap items-center gap-2">
              <span
                v-if="currentVersion"
                class="rounded-md bg-[var(--app-surface-2)] px-2 py-1 font-mono text-xs text-[var(--app-ink-soft)]"
                >v{{ currentVersion }}</span
              >
              <UIcon
                v-if="currentVersion && nextVersion"
                name="i-lucide-arrow-right"
                class="h-3 w-3 text-[var(--app-faint)]"
              />
              <span
                v-if="nextVersion"
                class="rounded-md bg-[var(--app-accent-soft)] px-2 py-1 font-mono text-xs text-[var(--app-accent-ink)]"
                >v{{ nextVersion }}</span
              >
            </div>
          </div>

          <div v-if="status === 'downloading'" class="space-y-3">
            <div class="flex items-center justify-between gap-3 text-xs text-[var(--app-ink-soft)]">
              <span class="font-medium text-[var(--app-ink)] tabular-nums">{{ downloadLabel }}</span>
              <span v-if="totalBytes && totalBytes > 0" class="tabular-nums">
                {{ (downloadedBytes / (1024 * 1024)).toFixed(1) }} / {{ (totalBytes / (1024 * 1024)).toFixed(1) }} Mo
              </span>
            </div>
            <div v-if="downloadPercent != null" class="h-2 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
              <div
                class="h-full rounded-full bg-[var(--app-accent)] transition-all"
                :style="{ width: `${downloadPercent}%` }"
              />
            </div>
          </div>

          <div class="flex flex-wrap justify-end gap-3">
            <button v-if="canDismiss" type="button" class="app-btn-secondary" @click="closePanel">Plus tard</button>
            <button v-if="status === 'available'" type="button" class="app-btn-primary" @click="installUpdate">
              Installer la mise à jour
            </button>
            <button v-if="status === 'installed'" type="button" class="app-btn-primary" @click="restartApp">
              Redémarrer l'application
            </button>
            <button v-if="status === 'error'" type="button" class="app-btn-primary" @click="installUpdate">
              Réessayer
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script lang="ts" setup>
import type { UseDesktopRuntimeReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import type { DownloadEvent, Update } from '@tauri-apps/plugin-updater'
import type { DevLeadHunterUpdaterStatus } from '~/types/DevLeadHunterDesktopUpdaterPanel'
import { check } from '@tauri-apps/plugin-updater'
import { relaunch } from '@tauri-apps/plugin-process'

const desktopRuntime: UseDesktopRuntimeReturn = useDesktopRuntime()
const isProdDesktop: ComputedRef<boolean> = desktopRuntime.isProdDesktop

const visible: Ref<boolean> = ref(false)
const status: Ref<DevLeadHunterUpdaterStatus> = ref('idle')
const currentVersion: Ref<string | null> = ref(null)
const nextVersion: Ref<string | null> = ref(null)
const errorMessage: Ref<string | null> = ref(null)
const pendingUpdate: Ref<Update | null> = shallowRef(null)
const downloadedBytes: Ref<number> = ref(0)
const totalBytes: Ref<number | null> = ref(null)

const downloadPercent: ComputedRef<number | null> = computed((): number | null => {
  const total: number | null = totalBytes.value
  if (total == null || total <= 0) {
    return null
  }
  return Math.min(100, Math.round((100 * downloadedBytes.value) / total))
})

const downloadLabel: ComputedRef<string> = computed((): string => {
  if (status.value !== 'downloading') {
    return ''
  }
  const pct: number | null = downloadPercent.value
  if (pct != null) {
    return `${pct}%`
  }
  if (downloadedBytes.value > 0) {
    return `${(downloadedBytes.value / (1024 * 1024)).toFixed(1)} Mo téléchargés`
  }
  return 'Préparation du téléchargement…'
})

const canDismiss: ComputedRef<boolean> = computed(
  (): boolean => status.value === 'available' || status.value === 'error',
)

const statusTitle: ComputedRef<string> = computed((): string => {
  if (status.value === 'available') return 'Mise à jour disponible'
  if (status.value === 'downloading') return 'Téléchargement et installation'
  if (status.value === 'installed') return 'Mise à jour installée'
  if (status.value === 'error') return 'Échec de la mise à jour'
  return 'Mise à jour'
})

const statusDescription: ComputedRef<string> = computed((): string => {
  if (status.value === 'available') {
    if (nextVersion.value && currentVersion.value) {
      return `Passez de la version ${currentVersion.value} à la version ${nextVersion.value}. L'application se fermera brièvement pour finaliser l'installation.`
    }
    return "Une nouvelle version est prête. L'application se fermera brièvement pour finaliser l'installation."
  }
  if (status.value === 'downloading') {
    return "Ne fermez pas DevLeadHunter pendant cette étape. Redémarrez l'application une fois l'installation terminée."
  }
  if (status.value === 'installed') {
    return 'Redémarrez DevLeadHunter pour charger la nouvelle version. Vos données et votre session sont conservées.'
  }
  if (status.value === 'error') {
    return errorMessage.value || 'Une erreur est survenue pendant la mise à jour.'
  }
  return ''
})

/**
 * Reset download progress metrics.
 */
function resetDownloadProgress(): void {
  downloadedBytes.value = 0
  totalBytes.value = null
}

/**
 * Update progress metrics from Tauri updater events.
 * @param event - Updater download event payload.
 */
function onDownloadEvent(event: DownloadEvent): void {
  if (event.event === 'Started') {
    const len: number | undefined = event.data.contentLength
    totalBytes.value = len != null && len > 0 ? len : null
    downloadedBytes.value = 0
  } else if (event.event === 'Progress') {
    downloadedBytes.value += event.data.chunkLength
  }
}

/**
 * Close the panel when dismissal is allowed.
 */
function closePanel(): void {
  if (!canDismiss.value) {
    return
  }
  visible.value = false
}

/**
 * Download and install the pending update package.
 */
async function installUpdate(): Promise<void> {
  if (!pendingUpdate.value) {
    return
  }

  try {
    status.value = 'downloading'
    errorMessage.value = null
    resetDownloadProgress()
    // Windows refuses to overwrite a live sidecar exe — kill it (and orphans) first.
    const { invoke }: { invoke: (command: string) => Promise<void> } = await import('@tauri-apps/api/core')
    await invoke('prepare_scraper_for_update')
    await pendingUpdate.value.downloadAndInstall(onDownloadEvent)
    status.value = 'installed'
  } catch (error) {
    status.value = 'error'
    errorMessage.value = error instanceof Error ? error.message : 'Download or installation failed.'
  }
}

/**
 * Restart the desktop app after a successful update.
 */
async function restartApp(): Promise<void> {
  try {
    await relaunch()
  } catch (error) {
    console.error('[Updater] relaunch() failed, reloading WebView as fallback:', error)
    window.location.reload()
  }
}

/**
 * Check for updates once per session and show the panel when available.
 */
async function checkForUpdate(): Promise<void> {
  // Dev has no updater endpoint, so checking there shows a spurious "Update failed" panel.
  if (!import.meta.client || !isProdDesktop.value) {
    return
  }

  if (window.sessionStorage.getItem('devleadhunter-updater-checked') === '1') {
    return
  }
  window.sessionStorage.setItem('devleadhunter-updater-checked', '1')

  errorMessage.value = null
  resetDownloadProgress()

  try {
    const update: Update | null = await check()
    pendingUpdate.value = update

    if (!update) {
      status.value = 'idle'
      return
    }

    currentVersion.value = update.currentVersion || null
    nextVersion.value = update.version || null
    status.value = 'available'
    visible.value = true
  } catch (error) {
    console.error('[Updater] Silent update check failed:', error)
    status.value = 'idle'
    pendingUpdate.value = null
  }
}

onMounted((): void => {
  void checkForUpdate()
})
</script>
