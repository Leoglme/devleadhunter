import type { CreditSettings } from '~/types'
import { ApiClient } from './api'

/**
 * Credit settings service for admin credit configuration management
 * @module services/creditSettingsService
 */

const CREDIT_SETTINGS_BASE_URL: string = '/api/v1/credit-settings'

/** The platform's cut on sales invoiced through a user's Stripe Connect account. */
export type PlatformCommission = {
  percent: number
  fixed_cents: number
}

export class CreditSettingsService {
  /**
   * Get current credit settings (public read access)
   * @returns Current credit settings
   * @throws If request fails
   */
  static async getCreditSettings(): Promise<CreditSettings> {
    return ApiClient.get<CreditSettings>(CREDIT_SETTINGS_BASE_URL)
  }

  /**
   * Update credit settings (admin only)
   * @param settingsData - Updated credit settings data
   * @returns Updated credit settings
   * @throws If request fails
   */
  static async updateCreditSettings(settingsData: Partial<CreditSettings>): Promise<CreditSettings> {
    return ApiClient.put<CreditSettings>(CREDIT_SETTINGS_BASE_URL, settingsData)
  }

  /**
   * Read the platform commission on Stripe Connect sales (admin only)
   * @returns The commission rate in percent
   * @throws If request fails
   */
  static async getPlatformCommission(): Promise<PlatformCommission> {
    return ApiClient.get<PlatformCommission>(`${CREDIT_SETTINGS_BASE_URL}/platform-commission`)
  }

  /**
   * Update the platform commission on Stripe Connect sales (admin only)
   * @param percent - Commission rate in percent
   * @param fixedCents - Fixed part of the commission, in cents
   * @throws If request fails
   */
  static async updatePlatformCommission(percent: number, fixedCents: number): Promise<void> {
    await ApiClient.put<CreditSettings>(CREDIT_SETTINGS_BASE_URL, {
      platform_commission_percent: percent,
      platform_commission_fixed_cents: fixedCents,
    })
  }
}
