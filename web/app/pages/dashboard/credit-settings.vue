<template>
  <div>
    <div class="mb-6">
      <p class="app-label flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Administration
      </p>
      <h1 class="app-page-title mt-2">Paramètres des crédits</h1>
    </div>

    <div v-if="!isLoading && creditSettings" class="card">
      <form @submit.prevent="handleSubmit">
        <div class="mb-6 grid grid-cols-1 gap-6 @2xl:grid-cols-2">
          <div>
            <label for="price-per-credit" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
              Prix par crédit (EUR)
            </label>
            <div class="relative">
              <span class="absolute top-1/2 left-3 -translate-y-1/2 text-[var(--app-ink-soft)]">€</span>
              <input
                id="price-per-credit"
                v-model.number="form.price_per_credit"
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="0.10"
                class="input-field pl-8"
              />
            </div>
            <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">Prix unitaire d'un crédit en euros</p>
          </div>

          <div>
            <label for="credits-per-search" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
              Crédits par recherche
            </label>
            <input
              id="credits-per-search"
              v-model.number="form.credits_per_search"
              type="number"
              min="1"
              required
              placeholder="5"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">
              Nombre de crédits requis pour lancer une recherche (minimum)
            </p>
          </div>

          <div>
            <label for="credits-per-result" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
              Crédits par résultat
            </label>
            <input
              id="credits-per-result"
              v-model.number="form.credits_per_result"
              type="number"
              min="1"
              required
              placeholder="1"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">Nombre de crédits requis par prospect trouvé</p>
          </div>

          <div>
            <label for="credits-per-email" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
              Crédits par email
            </label>
            <input
              id="credits-per-email"
              v-model.number="form.credits_per_email"
              type="number"
              min="1"
              required
              placeholder="3"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">Nombre de crédits requis pour envoyer un email</p>
          </div>

          <div>
            <label for="free-credits" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
              Crédits offerts à l'inscription
            </label>
            <input
              id="free-credits"
              v-model.number="form.free_credits_on_signup"
              type="number"
              min="0"
              required
              placeholder="15"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">Nombre de crédits offerts à chaque nouvel inscrit</p>
          </div>

          <div>
            <label for="minimum-credits-purchase" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
              Achat minimum de crédits
            </label>
            <input
              id="minimum-credits-purchase"
              v-model.number="form.minimum_credits_purchase"
              type="number"
              min="1"
              required
              placeholder="10"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">Nombre minimum de crédits achetables en une fois</p>
          </div>
        </div>

        <div class="flex flex-col gap-3 border-t border-[var(--app-line)] pt-4 @2xl:flex-row @2xl:justify-end">
          <button type="button" class="btn-secondary flex-1 sm:flex-none" :disabled="isSaving" @click="resetForm">
            Réinitialiser
          </button>
          <button
            type="submit"
            class="btn-primary flex-1 cursor-pointer sm:flex-none"
            :disabled="isSaving || !hasChanges"
          >
            <span v-if="isSaving">Enregistrement…</span>
            <span v-else>Enregistrer</span>
          </button>
        </div>
      </form>
    </div>

    <div v-if="!isLoading" class="card mt-6">
      <h2 class="text-base font-semibold text-[var(--app-ink)]">Commission plateforme</h2>
      <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
        Prélevée sur les ventes facturées via le compte Stripe Connect d'un utilisateur, au moment de l'émission de la
        facture. Sans effet sur vos propres ventes, encaissées par Qonto.
      </p>
      <form class="mt-4 flex flex-col gap-3 @2xl:flex-row @2xl:items-end" @submit.prevent="handleCommissionSubmit">
        <div class="sm:w-40">
          <label for="platform-commission" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
            Pourcentage
          </label>
          <div class="relative">
            <input
              id="platform-commission"
              v-model.number="commissionPercent"
              type="number"
              step="0.1"
              min="0"
              max="100"
              class="input-field pr-8"
              placeholder="10"
            />
            <span class="absolute top-1/2 right-3 -translate-y-1/2 text-[var(--app-ink-soft)]">%</span>
          </div>
        </div>
        <div class="sm:w-40">
          <label for="platform-commission-fixed" class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
            Montant fixe
          </label>
          <div class="relative">
            <span class="absolute top-1/2 left-3 -translate-y-1/2 text-[var(--app-ink-soft)]">€</span>
            <input
              id="platform-commission-fixed"
              v-model.number="commissionFixedEuros"
              type="number"
              step="0.5"
              min="0"
              class="input-field pl-8"
              placeholder="2"
            />
          </div>
        </div>
        <div class="sm:pb-1">
          <p class="text-xs text-[var(--app-ink-soft)]">
            {{ commissionExample }}
          </p>
        </div>
        <button
          type="submit"
          class="btn-primary cursor-pointer sm:ml-auto"
          :disabled="isSavingCommission || !hasCommissionChanges"
        >
          <span v-if="isSavingCommission">Enregistrement…</span>
          <span v-else>Enregistrer</span>
        </button>
      </form>
    </div>

    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-4">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-10 w-full rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-5/6 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-10 w-full rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <div v-if="error && !isLoading" class="card mt-6 border border-[var(--app-red)]/30 bg-[var(--app-red)]/10">
      <div class="flex items-center gap-2 text-[var(--app-red)]">
        <UIcon name="i-lucide-circle-alert" class="h-4 w-4 shrink-0" />
        <p>{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { CreditSettings } from '~/types'
import type { CreditSettingsForm } from '~/types/CreditSettingsPage'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted } from 'vue'
import type { PlatformCommission } from '~/services/creditSettingsService'
import { CreditSettingsService } from '~/services/creditSettingsService'
import { useToast } from '~/composables/useToast'

/**
 * Dashboard credit settings page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'super-admin'],
})

/**
 * Credit settings state
 */
const creditSettings: Ref<CreditSettings | null> = ref(null)
const isLoading: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)

/**
 * Form state
 */
const form: Ref<CreditSettingsForm> = ref({
  price_per_credit: 0.1,
  credits_per_search: 5,
  credits_per_result: 1,
  credits_per_email: 3,
  free_credits_on_signup: 15,
  minimum_credits_purchase: 10,
})

/**
 * Original form values for comparison
 */
const originalForm: Ref<CreditSettingsForm> = ref({
  price_per_credit: 0.1,
  credits_per_search: 5,
  credits_per_result: 1,
  credits_per_email: 3,
  free_credits_on_signup: 15,
  minimum_credits_purchase: 10,
})

/**
 * Platform commission on Stripe Connect sales (separate from credit pricing:
 * it is admin-only, where the credit settings above are read publicly).
 */
const commissionPercent: Ref<number> = ref(0)
const commissionFixedEuros: Ref<number> = ref(0)
const originalCommissionPercent: Ref<number> = ref(0)
const originalCommissionFixedEuros: Ref<number> = ref(0)
const isSavingCommission: Ref<boolean> = ref(false)

/**
 * Toast composable
 */
const toast: UseToastReturn = useToast()

/** Whether either commission field differs from what is stored. */
const hasCommissionChanges: ComputedRef<boolean> = computed((): boolean => {
  return (
    commissionPercent.value !== originalCommissionPercent.value ||
    commissionFixedEuros.value !== originalCommissionFixedEuros.value
  )
})

/** What the configured commission takes on a standard 500 € sale and on a small one. */
const commissionExample: ComputedRef<string> = computed((): string => {
  if (!commissionPercent.value && !commissionFixedEuros.value) return 'Aucune commission prélevée.'
  const cutOn: (saleEuros: number) => string = (saleEuros: number): string => {
    const cut: number = (saleEuros * commissionPercent.value) / 100 + commissionFixedEuros.value
    return Math.min(cut, saleEuros).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
  }
  return `Soit ${cutOn(500)} € sur une vente de 500 €, et ${cutOn(10)} € sur une vente de 10 €.`
})

/**
 * Check if form has changes
 */
const hasChanges: ComputedRef<boolean> = computed((): boolean => {
  return (
    form.value.price_per_credit !== originalForm.value.price_per_credit ||
    form.value.credits_per_search !== originalForm.value.credits_per_search ||
    form.value.credits_per_result !== originalForm.value.credits_per_result ||
    form.value.credits_per_email !== originalForm.value.credits_per_email ||
    form.value.free_credits_on_signup !== originalForm.value.free_credits_on_signup ||
    form.value.minimum_credits_purchase !== originalForm.value.minimum_credits_purchase
  )
})

/**
 * Load credit settings from API
 * @returns {Promise<void>}
 */
const loadCreditSettings: () => Promise<void> = async (): Promise<void> => {
  try {
    isLoading.value = true
    error.value = null
    creditSettings.value = await CreditSettingsService.getCreditSettings()

    // Update form with loaded values
    form.value = {
      price_per_credit: creditSettings.value.price_per_credit,
      credits_per_search: creditSettings.value.credits_per_search,
      credits_per_result: creditSettings.value.credits_per_result,
      credits_per_email: creditSettings.value.credits_per_email,
      free_credits_on_signup: creditSettings.value.free_credits_on_signup,
      minimum_credits_purchase: creditSettings.value.minimum_credits_purchase,
    }

    // Update original form for comparison
    originalForm.value = { ...form.value }
  } catch (err) {
    const errorMessage: string =
      err instanceof Error ? err.message : 'Erreur lors du chargement des paramètres de crédits'
    error.value = errorMessage
    toast.error(errorMessage)
  } finally {
    isLoading.value = false
  }
}

/**
 * Load the platform commission rate.
 * @returns {Promise<void>}
 */
const loadPlatformCommission: () => Promise<void> = async (): Promise<void> => {
  try {
    const commission: PlatformCommission = await CreditSettingsService.getPlatformCommission()
    commissionPercent.value = commission.percent
    commissionFixedEuros.value = commission.fixed_cents / 100
    originalCommissionPercent.value = commissionPercent.value
    originalCommissionFixedEuros.value = commissionFixedEuros.value
  } catch {
    // Non-blocking: the credit settings above stay usable.
  }
}

/**
 * Save the platform commission rate.
 * @returns {Promise<void>}
 */
const handleCommissionSubmit: () => Promise<void> = async (): Promise<void> => {
  try {
    isSavingCommission.value = true
    await CreditSettingsService.updatePlatformCommission(
      commissionPercent.value,
      Math.round(commissionFixedEuros.value * 100),
    )
    originalCommissionPercent.value = commissionPercent.value
    originalCommissionFixedEuros.value = commissionFixedEuros.value
    toast.success('Commission plateforme mise à jour')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour de la commission')
  } finally {
    isSavingCommission.value = false
  }
}

/**
 * Reset form to original values
 */
const resetForm: () => void = (): void => {
  if (originalForm.value) {
    form.value = { ...originalForm.value }
  }
}

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit: () => Promise<void> = async (): Promise<void> => {
  if (!creditSettings.value) return

  try {
    isSaving.value = true
    error.value = null

    // Prepare update data (only changed fields)
    const updateData: Partial<CreditSettings> = {}
    if (form.value.price_per_credit !== originalForm.value.price_per_credit) {
      updateData.price_per_credit = form.value.price_per_credit
    }
    if (form.value.credits_per_search !== originalForm.value.credits_per_search) {
      updateData.credits_per_search = form.value.credits_per_search
    }
    if (form.value.credits_per_result !== originalForm.value.credits_per_result) {
      updateData.credits_per_result = form.value.credits_per_result
    }
    if (form.value.credits_per_email !== originalForm.value.credits_per_email) {
      updateData.credits_per_email = form.value.credits_per_email
    }
    if (form.value.free_credits_on_signup !== originalForm.value.free_credits_on_signup) {
      updateData.free_credits_on_signup = form.value.free_credits_on_signup
    }
    if (form.value.minimum_credits_purchase !== originalForm.value.minimum_credits_purchase) {
      updateData.minimum_credits_purchase = form.value.minimum_credits_purchase
    }

    // Update credit settings
    const updated: CreditSettings = await CreditSettingsService.updateCreditSettings(updateData)

    // Update local state
    creditSettings.value = updated
    form.value = {
      price_per_credit: updated.price_per_credit,
      credits_per_search: updated.credits_per_search,
      credits_per_result: updated.credits_per_result,
      credits_per_email: updated.credits_per_email,
      free_credits_on_signup: updated.free_credits_on_signup,
      minimum_credits_purchase: updated.minimum_credits_purchase,
    }
    originalForm.value = { ...form.value }

    toast.success('Paramètres des crédits mis à jour')
  } catch (err) {
    const errorMessage: string = err instanceof Error ? err.message : 'Erreur lors de la mise à jour des paramètres'
    error.value = errorMessage
    toast.error(errorMessage)
  } finally {
    isSaving.value = false
  }
}

/**
 * Initialize component
 */
onMounted(() => {
  loadCreditSettings()
  loadPlatformCommission()
})
</script>
