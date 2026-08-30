/** A relance candidate row augmented with its per-row sending state. */
export type SmsCandidateRow = {
  prospect_id: number
  name: string
  city: string | null
  phone: string | null
  demo_url: string
  emailed_at: string
  sending: boolean
  sent: boolean
  error: string | null
}
