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

/** Whether the OVH registrar is wired, and which account it points at. */
export type RegistrarStatus = {
  configured: boolean
  account: string | null
}

/** Outcome of a domain registration. */
export type DomainRegisterResult = {
  domain: string
  ovh_order_id: number | null
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
   * Suggest a .fr domain from a business name (when the sale is not linked to a prospect).
   * @param name - The business name to derive candidates from.
   * @param useAi - Enrich with AI (« Suggérer » button); false for snappy as-you-type suggestions.
   * @returns The best pre-fill and the candidate list.
   */
  static async suggestForName(name: string, useAi: boolean = true): Promise<DomainSuggestions> {
    const params: URLSearchParams = new URLSearchParams({ name })
    if (!useAi) params.set('ai', 'false')
    return ApiClient.get<DomainSuggestions>(`/api/v1/domains/suggestions?${params.toString()}`)
  }

  /**
   * Check whether one .fr domain is free (AFNIC registry).
   * @param name - A domain or bare label (« chezmimon » or « chezmimon.fr »).
   * @returns The availability + estimated price.
   */
  static async checkAvailability(name: string): Promise<DomainCandidate> {
    return ApiClient.get<DomainCandidate>(`/api/v1/domains/availability?name=${encodeURIComponent(name)}`)
  }

  /**
   * Check the OVH registrar connection (no spend — a signed GET /me). Super-admin.
   * @returns Whether OVH is configured and which account it reaches.
   */
  static async registrarStatus(): Promise<RegistrarStatus> {
    return ApiClient.get<RegistrarStatus>('/api/v1/domains/registrar-status')
  }

  /**
   * Buy a domain and put a paid sale's site online in one action: register + DNS + deploy. Super-admin.
   * When orderId is given, the domain is saved on that sale and its linked demo is deployed to it.
   * @param domain - The full domain to provision.
   * @param orderId - The paid sale to bring online, when applicable.
   * @returns The order result.
   */
  static async provisionDomain(domain: string, orderId?: number | null): Promise<DomainRegisterResult> {
    return ApiClient.post<DomainRegisterResult>('/api/v1/domains/provision', { domain, order_id: orderId ?? null })
  }

  /**
   * Register a .fr domain on the operator's OVH account (fallback to the one-shot provision). Super-admin.
   * @param domain - The full .fr domain to buy.
   * @returns The order result.
   */
  static async registerDomain(domain: string): Promise<DomainRegisterResult> {
    return ApiClient.post<DomainRegisterResult>('/api/v1/domains/register', { domain })
  }

  /**
   * Point a domain's apex DNS at the Vercel demo-host. Super-admin. Run once the domain is active.
   * @param domain - The registered domain.
   * @returns A minimal acknowledgement.
   */
  static async pointDns(domain: string): Promise<{ status: string; domain: string }> {
    return ApiClient.post<{ status: string; domain: string }>('/api/v1/domains/point-dns', { domain })
  }
}
