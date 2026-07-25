<template>
  <div class="space-y-6">
    <UiLoader v-if="isLoading" />

    <template v-else>
      <!-- Connected state -->
      <section
        v-if="status && status.is_connected && status.connected_provider"
        class="space-y-5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <span
              class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-bold text-white"
              :style="{ background: providerBrand.color }"
            >
              {{ providerBrand.initial }}
            </span>
            <div>
              <p class="text-sm font-semibold text-[var(--app-ink)]">{{ providerBrand.label }} connecté</p>
              <p v-if="status.display_name" class="text-muted text-xs">{{ status.display_name }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="isSandbox" class="app-badge app-badge--info font-medium">Mode test</span>
            <span class="app-badge app-badge--success font-medium">
              <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
              Actif
            </span>
          </div>
        </div>

        <!-- Stripe: onboarding not finished yet -->
        <div v-if="isStripe && !status.stripe_charges_enabled" class="space-y-3">
          <UiCallout variant="warning">
            Votre compte Stripe n'accepte pas encore les paiements — la configuration hébergée par Stripe n'est pas
            terminée.
          </UiCallout>
          <button type="button" class="app-btn-secondary" :disabled="isBusy" @click="connectStripe">
            Terminer la configuration Stripe
          </button>
        </div>

        <!-- Qonto: IBAN printed on invoices (unreadable via API, captured here) -->
        <div v-if="isQonto" class="space-y-2">
          <label class="text-muted block text-xs font-medium" for="qonto-iban">IBAN (imprimé sur vos factures)</label>
          <div class="flex flex-wrap items-center gap-2">
            <input
              id="qonto-iban"
              v-model="ibanInput"
              type="text"
              inputmode="text"
              autocomplete="off"
              placeholder="FR76 …"
              class="input-field max-w-xs flex-1"
            />
            <button type="button" class="app-btn-secondary" :disabled="isBusy || !ibanInput.trim()" @click="saveIban">
              Enregistrer
            </button>
          </div>
          <p class="text-muted text-xs leading-relaxed">
            Nécessaire pour émettre vos factures : Qonto ne l'expose pas à l'API, vous le saisissez une fois.
          </p>
        </div>

        <div class="flex items-center justify-between border-t border-[var(--app-line)] pt-4">
          <p class="text-muted text-xs">Toute la facturation passe par {{ providerBrand.label }}.</p>
          <button type="button" class="btn-danger text-xs" :disabled="isBusy" @click="disconnect">Déconnecter</button>
        </div>
      </section>

      <!-- Disconnected: choose a provider -->
      <section v-else class="space-y-4">
        <div class="grid gap-3 sm:grid-cols-2">
          <button
            v-if="status?.qonto_available"
            type="button"
            class="provider-card"
            :disabled="isBusy"
            @click="connectQonto"
          >
            <span class="provider-card__logo" :style="{ background: QONTO_COLOR }">Q</span>
            <span class="provider-card__title">Connecter Qonto</span>
            <span class="provider-card__detail">Vos factures et liens de paiement, dans votre compte Qonto.</span>
          </button>

          <button type="button" class="provider-card" :disabled="isBusy" @click="connectStripe">
            <span class="provider-card__logo" :style="{ background: STRIPE_COLOR }">S</span>
            <span class="provider-card__title">Connecter Stripe</span>
            <span class="provider-card__detail">Encaissez vos ventes sur votre propre compte Stripe.</span>
          </button>
        </div>

        <UiCallout variant="info">
          Stripe n'est pas plateforme agréée pour la facturation électronique française : à partir de septembre 2027, la
          conformité de vos factures reste de votre responsabilité.
        </UiCallout>

        <details v-if="status?.qonto_available" class="group">
          <summary
            class="text-muted cursor-pointer text-xs font-medium underline underline-offset-4 hover:text-[var(--app-ink)]"
          >
            Options avancées — connecter Qonto par clé API
          </summary>
          <div class="mt-3 space-y-2 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
            <div class="grid gap-2 sm:grid-cols-2">
              <input v-model="apiLoginInput" type="text" placeholder="Login" autocomplete="off" class="input-field" />
              <input
                v-model="apiSecretInput"
                type="password"
                placeholder="Secret"
                autocomplete="off"
                class="input-field"
              />
            </div>
            <button
              type="button"
              class="app-btn-secondary"
              :disabled="isBusy || !apiLoginInput.trim() || !apiSecretInput.trim()"
              @click="saveApiKey"
            >
              Connecter par clé API
            </button>
            <p class="text-muted text-xs leading-relaxed">
              Solution de secours : la clé API émet les factures mais pas le bouton carte bancaire (paiement par
              virement).
            </p>
          </div>
        </details>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { PaymentProviderConfigEmits } from '~/types/PaymentProviderConfig'
import type { ComputedRef, EmitFn, Ref } from 'vue'
import type { PaymentAccountStatus, PaymentProviderKind } from '~/services/paymentAccountService'
import { computed, onMounted, ref } from 'vue'
import { PaymentAccountService } from '~/services/paymentAccountService'
import { useToast } from '~/composables/useToast'

/** Connect, tune and disconnect the user's encashment provider (Qonto or Stripe). */

const emit: EmitFn<PaymentProviderConfigEmits> = defineEmits<PaymentProviderConfigEmits>()

const QONTO_COLOR: string = '#12121A'
const STRIPE_COLOR: string = '#635BFF'

const toast: UseToastReturn = useToast()
const route: ReturnType<typeof useRoute> = useRoute()
const router: ReturnType<typeof useRouter> = useRouter()

const status: Ref<PaymentAccountStatus | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const isBusy: Ref<boolean> = ref(false)
const ibanInput: Ref<string> = ref('')
const apiLoginInput: Ref<string> = ref('')
const apiSecretInput: Ref<string> = ref('')

/** Currently connected provider, or null. */
const provider: ComputedRef<PaymentProviderKind | null> = computed(
  (): PaymentProviderKind | null => status.value?.connected_provider ?? null,
)
const isQonto: ComputedRef<boolean> = computed((): boolean => provider.value === 'qonto')
const isStripe: ComputedRef<boolean> = computed((): boolean => provider.value === 'stripe')
const isSandbox: ComputedRef<boolean> = computed((): boolean => status.value?.environment === 'sandbox')

/** Brand label, colour and initial for the connected provider. */
const providerBrand: ComputedRef<{ label: string; color: string; initial: string }> = computed(
  (): { label: string; color: string; initial: string } =>
    isStripe.value
      ? { label: 'Stripe', color: STRIPE_COLOR, initial: 'S' }
      : { label: 'Qonto', color: QONTO_COLOR, initial: 'Q' },
)

/**
 * Load the current status and reflect it in the local form + host.
 */
async function loadStatus(): Promise<void> {
  try {
    const next: PaymentAccountStatus = await PaymentAccountService.getStatus()
    status.value = next
    ibanInput.value = next.qonto_iban ?? ''
    emit('connected-change', next.is_connected)
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Chargement impossible')
  } finally {
    isLoading.value = false
  }
}

/**
 * Handle the OAuth / Stripe redirect flags on the URL, then clean them off.
 */
async function consumeRedirectFlags(): Promise<void> {
  const qonto: string | undefined = typeof route.query.qonto === 'string' ? route.query.qonto : undefined
  const stripe: string | undefined = typeof route.query.stripe === 'string' ? route.query.stripe : undefined
  if (!qonto && !stripe) return

  if (qonto === 'connected') toast.success('Qonto connecté')
  if (qonto === 'error') toast.error('La connexion Qonto a échoué')
  if (stripe === 'return' || stripe === 'refresh') {
    try {
      status.value = await PaymentAccountService.refreshStripe()
      emit('connected-change', status.value.is_connected)
      toast.success('Compte Stripe mis à jour')
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : 'Mise à jour Stripe impossible')
    }
  }
  await router.replace({ query: {} })
}

/**
 * Redirect to Qonto's OAuth consent screen.
 */
async function connectQonto(): Promise<void> {
  isBusy.value = true
  try {
    window.location.href = await PaymentAccountService.getQontoAuthorizeUrl()
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Connexion Qonto impossible')
    isBusy.value = false
  }
}

/**
 * Redirect to Stripe's hosted onboarding.
 */
async function connectStripe(): Promise<void> {
  isBusy.value = true
  try {
    window.location.href = await PaymentAccountService.startStripeOnboarding()
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Connexion Stripe impossible')
    isBusy.value = false
  }
}

/**
 * Store the Qonto invoicing IBAN.
 */
async function saveIban(): Promise<void> {
  isBusy.value = true
  try {
    status.value = await PaymentAccountService.setQontoIban(ibanInput.value.trim())
    toast.success('IBAN enregistré')
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Enregistrement impossible')
  } finally {
    isBusy.value = false
  }
}

/**
 * Connect Qonto through the admin-only API-key fallback.
 */
async function saveApiKey(): Promise<void> {
  isBusy.value = true
  try {
    status.value = await PaymentAccountService.setQontoApiKey(apiLoginInput.value.trim(), apiSecretInput.value.trim())
    apiLoginInput.value = ''
    apiSecretInput.value = ''
    emit('connected-change', status.value.is_connected)
    toast.success('Qonto connecté par clé API')
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Connexion impossible')
  } finally {
    isBusy.value = false
  }
}

/**
 * Disconnect the current provider and reset the form.
 */
async function disconnect(): Promise<void> {
  isBusy.value = true
  try {
    await PaymentAccountService.disconnect()
    ibanInput.value = ''
    await loadStatus()
    toast.success('Fournisseur déconnecté')
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Déconnexion impossible')
  } finally {
    isBusy.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadStatus()
  await consumeRedirectFlags()
})
</script>

<style scoped>
.provider-card {
  display: flex;
  cursor: pointer;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  border-radius: 0.75rem;
  border: 1px solid var(--app-line);
  background: var(--app-surface);
  padding: 1rem;
  text-align: left;
  transition:
    border-color 0.15s,
    background 0.15s;
}

.provider-card:hover:not(:disabled) {
  border-color: var(--app-ink-soft);
  background: var(--app-surface-2);
}

.provider-card:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.provider-card__logo {
  display: flex;
  height: 2.25rem;
  width: 2.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  font-weight: 700;
  color: #ffffff;
}

.provider-card__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--app-ink);
}

.provider-card__detail {
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--app-ink-soft);
}
</style>
