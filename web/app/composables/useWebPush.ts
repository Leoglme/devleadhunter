import { onMounted, ref, type Ref } from 'vue'
import { NotificationsService, type TestNotificationResult } from '~/services/notificationsService'
import {
  isPushSubscribed,
  isPushSupported,
  isStandalonePwa,
  subscribeToPush,
  unsubscribeFromPush,
} from '~/utils/webPush'

/** Reactive state and actions for the notifications switch. */
export type UseWebPush = {
  supported: Ref<boolean>
  standalone: Ref<boolean>
  subscribed: Ref<boolean>
  busy: Ref<boolean>
  error: Ref<string | null>
  enable: () => Promise<void>
  disable: () => Promise<void>
  toggle: (value: boolean) => Promise<void>
  sendTest: () => Promise<TestNotificationResult>
}

/**
 * Manage the push subscription for the current device (settings switch).
 * @returns Support flags, subscription state and enable/disable/toggle/test actions.
 */
export function useWebPush(): UseWebPush {
  const supported: Ref<boolean> = ref(false)
  const standalone: Ref<boolean> = ref(false)
  const subscribed: Ref<boolean> = ref(false)
  const busy: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)

  /**
   * Read current support and subscription state.
   * @returns Nothing.
   */
  async function refresh(): Promise<void> {
    if (!import.meta.client) {
      return
    }
    supported.value = isPushSupported()
    standalone.value = isStandalonePwa()
    subscribed.value = await isPushSubscribed()
  }

  /**
   * Request permission (the required user gesture) and subscribe.
   * @returns Nothing.
   */
  async function enable(): Promise<void> {
    if (!supported.value || busy.value) {
      return
    }
    busy.value = true
    error.value = null
    try {
      const permission: NotificationPermission = await Notification.requestPermission()
      if (permission !== 'granted') {
        error.value = 'permission'
        return
      }
      const ok: boolean = await subscribeToPush()
      if (!ok) {
        error.value = 'not-configured'
        return
      }
      subscribed.value = true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'error'
    } finally {
      busy.value = false
    }
  }

  /**
   * Turn notifications off on this device (temporary — remembered locally).
   * @returns Nothing.
   */
  async function disable(): Promise<void> {
    if (busy.value) {
      return
    }
    busy.value = true
    error.value = null
    try {
      await unsubscribeFromPush()
      subscribed.value = false
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'error'
    } finally {
      busy.value = false
    }
  }

  /**
   * Switch handler.
   * @param value - Desired on/off state.
   * @returns Nothing.
   */
  async function toggle(value: boolean): Promise<void> {
    if (value) {
      await enable()
    } else {
      await disable()
    }
  }

  /**
   * Send a test notification to this user's devices.
   * @returns The diagnostic (configured flag, device count, delivered/failed counts).
   */
  async function sendTest(): Promise<TestNotificationResult> {
    return NotificationsService.test()
  }

  onMounted(refresh)

  return { supported, standalone, subscribed, busy, error, enable, disable, toggle, sendTest }
}
