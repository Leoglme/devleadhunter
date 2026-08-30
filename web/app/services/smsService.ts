import { ApiClient } from './api'

/** The user's SMS sender configuration. */
export type SmsConfig = {
  sender: string
  enabled: boolean
  provider_ready: boolean
}

/** Payload to update the SMS sender configuration. */
export type SmsConfigUpdate = {
  sender: string
  enabled: boolean
}

/** A prospect eligible for an SMS relance. */
export type SmsRelanceCandidate = {
  prospect_id: number
  name: string
  city: string | null
  phone: string | null
  demo_url: string
  emailed_at: string
}

/** Outcome of a single relance send. */
export type SmsSendResult = {
  sent: boolean
  reason: string | null
}

/** Outcome of a bulk relance send. */
export type SmsBulkSendResult = {
  sent: number
  skipped: number
}

/** SMS relance channel — sender config, eligible prospects, sending. */
export class SmsService {
  /**
   * Fetch the current user's SMS sender configuration.
   * @returns The SMS config.
   */
  static async getConfig(): Promise<SmsConfig> {
    return ApiClient.get<SmsConfig>('/api/v1/sms/config')
  }

  /**
   * Update the SMS sender + enable flag.
   * @param payload - The new configuration.
   * @returns The saved configuration.
   */
  static async updateConfig(payload: SmsConfigUpdate): Promise<SmsConfig> {
    return ApiClient.put<SmsConfig>('/api/v1/sms/config', payload)
  }

  /**
   * List prospects eligible for an SMS relance.
   * @param afterDays - Minimum age in days of the unanswered email.
   * @returns The eligible candidates.
   */
  static async listCandidates(afterDays: number = 30): Promise<SmsRelanceCandidate[]> {
    return ApiClient.get<SmsRelanceCandidate[]>(`/api/v1/sms/relance-candidates?after_days=${afterDays}`)
  }

  /**
   * Send a relance SMS to one prospect.
   * @param prospectId - The prospect id.
   * @returns The send result.
   */
  static async sendRelance(prospectId: number): Promise<SmsSendResult> {
    return ApiClient.post<SmsSendResult>(`/api/v1/sms/relance/${prospectId}`, {})
  }

  /**
   * Send relance SMS to all eligible prospects, up to a limit.
   * @param limit - Maximum number to send.
   * @returns The bulk send result.
   */
  static async sendRelanceBulk(limit: number = 20): Promise<SmsBulkSendResult> {
    return ApiClient.post<SmsBulkSendResult>(`/api/v1/sms/relance?limit=${limit}`, {})
  }
}
