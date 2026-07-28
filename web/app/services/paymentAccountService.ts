import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/payment-accounts'

/** Encashment provider a user sells through. */
export type PaymentProviderKind = 'qonto' | 'stripe'

/** Connection status for the billing settings page (never carries secrets). */
export type PaymentAccountStatus = {
  connected_provider: PaymentProviderKind | null
  is_connected: boolean
  environment: string | null
  display_name: string | null
  qonto_available: boolean
  qonto_iban: string | null
  has_qonto_api_key: boolean
  stripe_charges_enabled: boolean
  stripe_details_submitted: boolean
}

/** A URL to redirect the browser to (OAuth authorize or Stripe onboarding). */
type ConnectUrl = { url: string }

export class PaymentAccountService {
  /**
   * Fetch the current user's encashment-provider status.
   * @returns The connection status (all flags false when nothing is connected).
   */
  static async getStatus(): Promise<PaymentAccountStatus> {
    return ApiClient.get<PaymentAccountStatus>(`${BASE_URL}/status`)
  }

  /**
   * Get the Qonto OAuth authorization URL to redirect the admin to.
   * @returns The authorization URL.
   */
  static async getQontoAuthorizeUrl(): Promise<string> {
    const response: ConnectUrl = await ApiClient.post<ConnectUrl>(`${BASE_URL}/qonto/authorize`, {})
    return response.url
  }

  /**
   * Connect Qonto with an API key (admin-only fallback for OAuth).
   * @param login - Qonto API-key login.
   * @param secret - Qonto API-key secret.
   * @returns The refreshed status.
   */
  static async setQontoApiKey(login: string, secret: string): Promise<PaymentAccountStatus> {
    return ApiClient.post<PaymentAccountStatus>(`${BASE_URL}/qonto/api-key`, { login, secret })
  }

  /**
   * Store the IBAN printed on Qonto invoices.
   * @param iban - The IBAN as entered.
   * @returns The refreshed status.
   */
  static async setQontoIban(iban: string): Promise<PaymentAccountStatus> {
    return ApiClient.put<PaymentAccountStatus>(`${BASE_URL}/qonto/iban`, { iban })
  }

  /**
   * Start (or resume) Stripe Connect onboarding.
   * @returns The hosted onboarding URL to redirect the browser to.
   */
  static async startStripeOnboarding(): Promise<string> {
    const response: ConnectUrl = await ApiClient.post<ConnectUrl>(`${BASE_URL}/stripe/onboard`, {})
    return response.url
  }

  /**
   * Re-read the Stripe account status after onboarding returns.
   * @returns The refreshed status.
   */
  static async refreshStripe(): Promise<PaymentAccountStatus> {
    return ApiClient.post<PaymentAccountStatus>(`${BASE_URL}/stripe/refresh`, {})
  }

  /**
   * Disconnect and forget the current user's encashment provider.
   */
  static async disconnect(): Promise<void> {
    await ApiClient.delete(BASE_URL)
  }
}
