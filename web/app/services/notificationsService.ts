/**
 * Notifications service — HTTP client for Web Push (VAPID) subscription + test.
 * @module services/notificationsService
 */
import { ApiClient } from './api'

/** Public VAPID key and whether push is configured server-side. */
export type VapidKeyResponse = {
  public_key: string | null
  configured: boolean
}

/** A browser push subscription payload sent to the API. */
export type PushSubscriptionPayload = {
  endpoint: string
  keys: { p256dh: string; auth: string }
  user_agent?: string
}

/** Diagnostic returned by the test endpoint (delivered/failed = the push service's verdict). */
export type TestNotificationResult = {
  configured: boolean
  subscriptions: number
  delivered: number
  failed: number
  detail: string | null
}

/** HTTP client for the /notifications API resource. */
export class NotificationsService {
  /**
   * Fetch the public VAPID key needed to subscribe.
   *
   * @returns The public key and whether push is configured server-side.
   */
  static async getVapidKey(): Promise<VapidKeyResponse> {
    return ApiClient.get<VapidKeyResponse>('/api/v1/notifications/vapid-key')
  }

  /**
   * Register (or refresh) a browser push subscription for the current user.
   *
   * @param payload - Endpoint + encryption keys + optional device hint.
   * @returns Nothing.
   */
  static async subscribe(payload: PushSubscriptionPayload): Promise<void> {
    await ApiClient.post('/api/v1/notifications/subscribe', payload)
  }

  /**
   * Remove a browser push subscription for the current user.
   *
   * @param endpoint - The subscription endpoint to unregister.
   * @returns Nothing.
   */
  static async unsubscribe(endpoint: string): Promise<void> {
    await ApiClient.post('/api/v1/notifications/unsubscribe', { endpoint })
  }

  /**
   * Send a test notification now and return the delivery diagnostic.
   *
   * @returns Whether push is configured, the device count, and delivered/failed counts.
   */
  static async test(): Promise<TestNotificationResult> {
    return ApiClient.post<TestNotificationResult>('/api/v1/notifications/test', {})
  }
}
