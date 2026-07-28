import type { SendPolicy } from '~/types/Automation'
import { SEND_POLICY_DAY_LABELS } from '~/constants/sendPolicyDayLabels'

/** Below this many contiguous days, listing them reads better than a range. */
const SHORTEST_DAY_RANGE: number = 3

/**
 * Human list of the sending days, collapsed to a range when they are contiguous.
 * @param days - Selected weekday indexes, 0 = Monday.
 * @returns A label such as « Lun – Ven », « Lun, Mer » or « aucun jour ».
 */
export function formatSendPolicyDays(days: number[]): string {
  const sorted: number[] = [...days].sort((first: number, second: number): number => first - second)
  if (sorted.length === 0) return 'aucun jour'
  const labels: string[] = sorted.map((day: number): string => SEND_POLICY_DAY_LABELS[day] ?? '')
  const isContiguous: boolean = sorted.every(
    (day: number, index: number): boolean => index === 0 || day === (sorted[index - 1] ?? 0) + 1,
  )
  if (isContiguous && sorted.length >= SHORTEST_DAY_RANGE) return `${labels[0]} – ${labels[labels.length - 1]}`
  return labels.join(', ')
}

/**
 * One-line summary of the cadence emails will actually follow.
 * @param policy - The user's send policy, null while it loads.
 * @returns A readable summary, or a neutral fallback when the policy is unknown.
 */
export function formatSendPolicySummary(policy: SendPolicy | null): string {
  if (!policy) return 'selon vos réglages d’envoi'
  const days: string = formatSendPolicyDays(policy.days_of_week)
  return `${policy.daily_cap}/jour · ${policy.window_start_hour}h-${policy.window_end_hour}h · ${days}`
}
