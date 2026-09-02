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

/** Visual level of a stored notification. */
export type NotificationLevel = 'info' | 'success' | 'warning' | 'error'

/** One persisted in-app notification (history log). */
export type NotificationItem = {
  id: number
  category: string
  level: NotificationLevel
  title: string
  body: string
  url: string
  read: boolean
  created_at: string
}

/** A page of notification history plus the current unread count. */
export type NotificationHistory = {
  items: NotificationItem[]
  unread_count: number
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

  /**
   * Fetch a page of the current user's notification history (newest first).
   *
   * @param before - Return notifications with an id strictly below this (cursor for "load more").
   * @param limit - Page size (1..50).
   * @returns The page of notifications and the unread count.
   */
  static async getHistory(before?: number, limit: number = 20): Promise<NotificationHistory> {
    return ApiClient.get<NotificationHistory>('/api/v1/notifications/history', { params: { before, limit } })
  }

  /**
   * Fetch a single notification by id (opened from a push tap).
   *
   * @param id - The notification id.
   * @returns The notification.
   */
  static async getOne(id: number): Promise<NotificationItem> {
    return ApiClient.get<NotificationItem>(`/api/v1/notifications/${id}`)
  }

  /**
   * Mark a single notification as read.
   *
   * @param id - The notification id.
   * @returns Nothing.
   */
  static async markRead(id: number): Promise<void> {
    await ApiClient.patch(`/api/v1/notifications/${id}/read`, {})
  }

  /**
   * Mark every unread notification of the current user as read.
   *
   * @returns Nothing.
   */
  static async markAllRead(): Promise<void> {
    await ApiClient.post('/api/v1/notifications/read-all', {})
  }
}
