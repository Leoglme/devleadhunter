/**
 * Format an amount in cents as a euro string (« 12 € » / « 12.34 € »).
 * @param cents - Amount in cents, or null when unknown.
 * @returns The formatted euro amount, or « — » when null.
 */
export function formatEuros(cents: number | null): string {
  if (cents == null) return '—'
  const euros: number = cents / 100
  return `${euros % 1 === 0 ? euros.toFixed(0) : euros.toFixed(2)} €`
}
