import type { EmailResendResult } from '~/types'
import { ApiClient } from './api'

/**
 * Read/act on individual sent-email logs (the « Suivi des e-mails » page).
 */
export class EmailLogsService {
  /**
   * Re-send an email log's message, optionally to a corrected address.
   * A different address is saved as the prospect's primary, so the pending follow-up reaches it too.
   * @param logId The email log to re-send.
   * @param email Address to send to; when empty, the prospect's current primary address is used.
   * @returns The send result (success flag + optional error).
   */
  static async resendEmailLog(logId: number, email?: string): Promise<EmailResendResult> {
    return ApiClient.post<EmailResendResult>(`/api/v1/emails/logs/${logId}/resend`, {
      email: email && email.trim() ? email.trim() : null,
    })
  }
}
