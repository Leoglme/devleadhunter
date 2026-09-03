import { ApiClient } from '~/services/api'

/** Availability + estimated price for one .fr domain. */
export type DomainCandidate = {
  domain: string
  available: boolean | null
  price_eur: number | null
}

/** Suggestion response: the best pre-fill plus every candidate considered. */
export type DomainSuggestions = {
  suggested: string | null
  candidates: DomainCandidate[]
}

/** Domain suggestion + availability for the post-sale go-live. */
export class DomainsService {
  /**
   * Suggest a .fr domain for a prospect (logical name + AI, availability-checked).
   * @param prospectId - The prospect to suggest a domain for.
   * @returns The best pre-fill and the candidate list.
   */
  static async suggestForProspect(prospectId: number): Promise<DomainSuggestions> {
    return ApiClient.get<DomainSuggestions>(`/api/v1/domains/suggestions?prospect_id=${prospectId}`)
  }

  /**
   * Check whether one .fr domain is free (AFNIC registry).
   * @param name - A domain or bare label (« chezmimon » or « chezmimon.fr »).
   * @returns The availability + estimated price.
   */
  static async checkAvailability(name: string): Promise<DomainCandidate> {
    return ApiClient.get<DomainCandidate>(`/api/v1/domains/availability?name=${encodeURIComponent(name)}`)
  }
}
