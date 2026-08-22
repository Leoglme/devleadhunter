import { watch } from 'vue'
import { isPushDisabledLocally, isPushSupported, subscribeToPush } from '~/utils/webPush'

/**
 * Auto-subscribe to Web Push once permission is granted (so notifications stay "on by default"),
 * unless the user turned them off on this device. First-time permission still needs the settings
 * switch (an iOS user-gesture requirement). No-op on the desktop build and during SSR.
 */
export default defineNuxtPlugin((): void => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

  /**
   * Ensure a fresh push subscription exists when eligible.
   * @returns Nothing.
   */
  async function ensureSubscribed(): Promise<void> {
    if (!import.meta.client || config.public.isDesktop) {
      return
    }
    if (!isPushSupported() || isPushDisabledLocally()) {
      return
    }
    if (Notification.permission !== 'granted' || !userStore.token) {
      return
    }
    await subscribeToPush().catch((): void => {})
  }

  void ensureSubscribed()
  watch(
    (): string | null => userStore.token,
    (): void => {
      void ensureSubscribed()
    },
  )
})
