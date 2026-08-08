import type {
  CompanyBillingPrefill,
  RegistryCompany,
  RegistryEstablishment,
  RegistrySearchResponse,
} from '~/types/CompanyRegistryLookup'
import { isCompleteTaxId } from '~/utils/taxIdUtils'

const REGISTRY_SEARCH_URL: string = 'https://recherche-entreprises.api.gouv.fr/search'

/**
 * Build a street line from structured registry fields, falling back to the raw address.
 * @param establishment - Registry establishment block.
 * @returns A street address without postal code or city.
 */
function buildStreetLine(establishment: RegistryEstablishment): string {
  const structuredParts: string[] = [
    establishment.numero_voie,
    establishment.type_voie,
    establishment.libelle_voie,
  ].filter((part: string | undefined): part is string => Boolean(part?.trim()))

  if (structuredParts.length > 0) {
    return structuredParts.join(' ')
  }

  const rawAddress: string = (establishment.adresse ?? '').trim()
  const postalCode: string = establishment.code_postal ?? ''
  const city: string = establishment.libelle_commune ?? ''

  if (!rawAddress) {
    return ''
  }

  let street: string = rawAddress
  if (postalCode) {
    street = street.replace(new RegExp(`\\b${postalCode}\\b`), '')
  }
  if (city) {
    street = street.replace(new RegExp(`${city}$`, 'i'), '')
  }

  return street.replace(/\s+/g, ' ').trim()
}

/**
 * Resolve the establishment that matches a SIREN or SIRET query.
 * @param compactTaxId - Nine- or fourteen-digit identifier.
 * @param company - Company returned by the registry search.
 * @returns The matching establishment, if any.
 */
function resolveEstablishment(compactTaxId: string, company: RegistryCompany): RegistryEstablishment | null {
  if (compactTaxId.length === 14) {
    if (company.siege?.siret === compactTaxId) {
      return company.siege
    }
    return (
      company.matching_etablissements?.find(
        (establishment: RegistryEstablishment): boolean => establishment.siret === compactTaxId,
      ) ?? null
    )
  }

  return company.siege ?? null
}

/**
 * Pick the billing company name from registry fields.
 * @param company - Company returned by the registry search.
 * @returns The most accurate legal name available.
 */
function pickCompanyName(company: RegistryCompany): string {
  return (company.nom_raison_sociale || company.nom_complet).trim()
}

/**
 * Look up a French company by SIREN or SIRET and map it to billing fields.
 * @param compactTaxId - Validated nine- or fourteen-digit identifier.
 * @param abortSignal - Optional abort signal for in-flight requests.
 * @returns Billing prefill data, or null when nothing matches.
 */
export async function lookupCompanyBilling(
  compactTaxId: string,
  abortSignal?: AbortSignal,
): Promise<CompanyBillingPrefill | null> {
  if (!isCompleteTaxId(compactTaxId)) {
    return null
  }

  const response: RegistrySearchResponse = await $fetch<RegistrySearchResponse>(REGISTRY_SEARCH_URL, {
    query: {
      q: compactTaxId,
      page: 1,
      per_page: 10,
    },
    signal: abortSignal,
  })

  const company: RegistryCompany | undefined = response.results?.[0]
  if (!company) {
    return null
  }

  if (compactTaxId.length === 9 && company.siren !== compactTaxId) {
    return null
  }

  const establishment: RegistryEstablishment | null = resolveEstablishment(compactTaxId, company)
  if (compactTaxId.length === 14 && !establishment) {
    return null
  }

  const addressSource: RegistryEstablishment | undefined = establishment ?? company.siege
  if (!addressSource) {
    return null
  }

  return {
    name: pickCompanyName(company),
    address: buildStreetLine(addressSource),
    zip_code: addressSource.code_postal ?? '',
    city: addressSource.libelle_commune ?? '',
    tax_id: compactTaxId.length === 14 ? compactTaxId : company.siren,
    vat_number: company.tva?.[0] ?? null,
  }
}
