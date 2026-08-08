import type { AddressSuggestion } from '~/types/AddressAutocompleteInput'
import type { PostalCodeCitySuggestion } from '~/types/PostalCodeAutocompleteInput'

type BanFeatureProperties = {
  label?: string
  name?: string
  postcode?: string
  city?: string
}

type BanFeature = {
  properties?: BanFeatureProperties
}

type BanSearchResponse = {
  features?: BanFeature[]
}

type CommuneByPostalCode = {
  nom?: string
  codesPostaux?: string[]
}

/** Default number of address suggestions returned by the BAN API. */
const DEFAULT_ADDRESS_LIMIT: number = 6

/** French postal codes are exactly five digits. */
const POSTAL_CODE_LENGTH: number = 5

/**
 * Search French street addresses through the Base Adresse Nationale (BAN).
 * @param query - Free-text address query typed by the user.
 * @param limit - Maximum number of suggestions to return.
 * @returns Matching address suggestions, newest query wins at the caller level.
 */
export async function searchAddressSuggestions(
  query: string,
  limit: number = DEFAULT_ADDRESS_LIMIT,
): Promise<AddressSuggestion[]> {
  const trimmedQuery: string = query.trim()
  if (trimmedQuery.length < 2) {
    return []
  }

  const response: BanSearchResponse = await $fetch<BanSearchResponse>('https://api-adresse.data.gouv.fr/search/', {
    query: {
      q: trimmedQuery,
      limit,
    },
  })

  return (response.features ?? [])
    .map((feature: BanFeature): AddressSuggestion | null => {
      const properties: BanFeatureProperties | undefined = feature.properties
      if (!properties?.label || !properties.name || !properties.postcode || !properties.city) {
        return null
      }
      return {
        label: properties.label,
        name: properties.name,
        postcode: properties.postcode,
        city: properties.city,
      }
    })
    .filter((suggestion: AddressSuggestion | null): suggestion is AddressSuggestion => suggestion !== null)
}

/**
 * List communes that share a French postal code (geo.api.gouv.fr).
 * @param postalCode - Five-digit postal code.
 * @returns Communes linked to this postal code, sorted by name.
 */
export async function searchCitiesByPostalCode(postalCode: string): Promise<PostalCodeCitySuggestion[]> {
  const trimmedCode: string = postalCode.trim()
  if (!/^\d{5}$/.test(trimmedCode)) {
    return []
  }

  const communes: CommuneByPostalCode[] = await $fetch<CommuneByPostalCode[]>('https://geo.api.gouv.fr/communes', {
    query: {
      codePostal: trimmedCode,
      fields: 'nom,codesPostaux',
      limit: 100,
    },
  })

  return communes
    .filter((commune: CommuneByPostalCode): commune is PostalCodeCitySuggestion => Boolean(commune.nom))
    .map(
      (commune: CommuneByPostalCode): PostalCodeCitySuggestion => ({
        nom: commune.nom as string,
        codesPostaux: commune.codesPostaux ?? [trimmedCode],
      }),
    )
    .sort((left: PostalCodeCitySuggestion, right: PostalCodeCitySuggestion): number =>
      left.nom.localeCompare(right.nom, 'fr'),
    )
}

/** Length required before a postal-code lookup is attempted. */
export const POSTAL_CODE_LOOKUP_LENGTH: number = POSTAL_CODE_LENGTH
