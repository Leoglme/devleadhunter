<template>
  <div class="space-y-5">
    <UiLoader v-if="isLoading" />

    <section v-else-if="connectedProvider" class="app-card overflow-hidden">
      <header class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--app-line)] px-5 py-4">
        <div class="flex min-w-0 items-center gap-3.5">
          <span :class="['flex h-11 shrink-0 items-center rounded-xl px-4', providerPlateClass]">
            <UiQontoLogo v-if="isQonto" class="h-4 w-auto text-white" />
            <UiStripeLogo v-else class="h-4 w-auto text-white" />
          </span>
          <div class="min-w-0">
            <p class="app-label">Compte connecté</p>
            <p class="mt-0.5 truncate text-sm font-semibold text-[var(--app-ink)]">
              {{ status?.display_name || providerName }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span v-if="isSandbox" class="app-badge app-badge--progress font-medium">Mode test</span>
          <span v-if="isStripeIncomplete" class="app-badge app-badge--progress font-medium">
            <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5" />
            À terminer
          </span>
          <span v-else class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Actif
          </span>
        </div>
      </header>

      <div class="space-y-5 px-5 py-5">
        <div v-if="isStripeIncomplete" class="space-y-3">
          <UiCallout variant="warning">
            Votre compte Stripe n'accepte pas encore les paiements — la configuration hébergée par Stripe n'est pas
            terminée.
          </UiCallout>
          <button type="button" class="app-btn-secondary" :disabled="isBusy" @click="connectProvider('stripe')">
            <UIcon v-if="pendingProvider === 'stripe'" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
            Terminer la configuration Stripe
          </button>
        </div>

        <div v-if="isQonto" class="space-y-2">
          <label for="qonto-iban" class="app-label block">IBAN imprimé sur vos factures</label>
          <div class="flex flex-wrap items-center gap-2">
            <input
              id="qonto-iban"
              v-model="ibanInput"
              type="text"
              inputmode="text"
              autocomplete="off"
              placeholder="FR76 3000 1007 9412 3456 7890 185"
              class="app-input flex-1 basis-full font-[family-name:var(--app-font-mono)] tracking-[0.02em] sm:max-w-xs sm:basis-auto"
            />
            <button type="button" class="app-btn-secondary" :disabled="isBusy || !ibanInput.trim()" @click="saveIban">
              Enregistrer
            </button>
          </div>
          <p class="text-muted text-xs leading-relaxed">
            Qonto ne l'expose pas à son API : vous le saisissez une fois, il apparaît ensuite sur chaque facture.
          </p>
        </div>

        <UiCallout v-if="isQonto && status?.has_qonto_api_key" variant="neutral" icon="i-lucide-key-round">
          Connexion par clé API : vos factures partent bien, mais sans bouton de paiement par carte — vos clients
          règlent par virement.
        </UiCallout>
      </div>

      <footer
        class="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--app-line)] bg-[var(--app-bg)] px-5 py-3.5"
      >
        <p class="text-muted text-xs">Toute la facturation passe par {{ providerName }}.</p>
        <button
          type="button"
          class="cursor-pointer text-xs font-medium text-[var(--app-red)] underline underline-offset-4 transition-opacity hover:opacity-75 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="isBusy"
          @click="disconnect"
        >
          Déconnecter
        </button>
      </footer>
    </section>

    <section v-else class="space-y-4">
      <div class="grid gap-3" :class="availableCards.length > 1 ? 'sm:grid-cols-2' : ''">
        <button
          v-for="card in availableCards"
          :key="card.provider"
          type="button"
          class="group flex cursor-pointer flex-col rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5 text-left transition-[border-color,box-shadow] focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:outline-none enabled:hover:border-[var(--app-ink-soft)] enabled:hover:shadow-[var(--app-shadow-soft)] disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isBusy"
          @click="connectProvider(card.provider)"
        >
          <span :class="['flex h-11 items-center self-start rounded-xl px-4', PROVIDER_PLATE_CLASS[card.provider]]">
            <UiQontoLogo v-if="card.provider === 'qonto'" class="h-4 w-auto text-white" />
            <UiStripeLogo v-else class="h-4 w-auto text-white" />
          </span>

          <span class="flex flex-1 flex-col">
            <span class="app-label mt-4">
              {{ card.role }}
              <span v-if="card.caveat" class="text-[var(--app-accent-ink)]">*</span>
            </span>
            <span class="text-muted mt-2 text-sm leading-relaxed">{{ card.pitch }}</span>

            <span class="mt-4 flex flex-col gap-1.5">
              <span v-for="benefit in card.benefits" :key="benefit" class="flex items-start gap-2">
                <UIcon name="i-lucide-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-green)]" />
                <span class="text-xs leading-relaxed text-[var(--app-ink)]">{{ benefit }}</span>
              </span>
            </span>
          </span>

          <span
            class="mt-5 flex items-center justify-between gap-2 border-t border-[var(--app-line)] pt-4 text-sm font-semibold text-[var(--app-ink)]"
          >
            {{ pendingProvider === card.provider ? 'Redirection…' : `Connecter ${PROVIDER_NAME[card.provider]}` }}
            <UIcon
              :name="pendingProvider === card.provider ? 'i-lucide-loader-circle' : 'i-lucide-arrow-right'"
              class="h-3.5 w-3.5 shrink-0 transition-transform"
              :class="pendingProvider === card.provider ? 'animate-spin' : 'group-hover:translate-x-0.5'"
            />
          </span>
        </button>
      </div>

      <p v-for="caveat in caveats" :key="caveat" class="text-muted flex items-start gap-2 text-[11px] leading-relaxed">
        <span aria-hidden="true" class="font-[family-name:var(--app-font-mono)] text-[var(--app-accent-ink)]">*</span>
        {{ caveat }}
      </p>

      <details v-if="status?.qonto_available" class="group app-card overflow-hidden">
        <summary
          class="text-muted flex list-none items-center justify-between gap-3 px-4 py-3 text-xs font-medium transition-colors select-none hover:text-[var(--app-ink)] [&::-webkit-details-marker]:hidden"
        >
          <span class="flex items-center gap-2">
            <UIcon name="i-lucide-key-round" class="h-3.5 w-3.5 shrink-0" />
            Connecter Qonto par clé API
            <span class="app-badge px-2 py-0 text-[10px]">Secours</span>
          </span>
          <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 shrink-0 transition-transform group-open:rotate-180" />
        </summary>

        <div class="space-y-4 border-t border-[var(--app-line)] px-4 py-4">
          <p class="text-muted text-xs leading-relaxed">
            À utiliser si la connexion ci-dessus échoue : la clé API émet vos factures, mais sans bouton de paiement par
            carte — vos clients règlent alors par virement.
          </p>
          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <label for="qonto-api-login" class="app-label mb-1.5 block">Identifiant</label>
              <input
                id="qonto-api-login"
                v-model="apiLoginInput"
                type="text"
                autocomplete="off"
                placeholder="votre-entreprise-1234"
                class="app-input"
              />
            </div>
            <div>
              <label for="qonto-api-secret" class="app-label mb-1.5 block">Clé secrète</label>
              <UiPasswordInput id="qonto-api-secret" v-model="apiSecretInput" placeholder="••••••••••••••••" />
            </div>
          </div>
          <button
            type="button"
            class="app-btn-secondary"
            :disabled="isBusy || !apiLoginInput.trim() || !apiSecretInput.trim()"
            @click="saveApiKey"
          >
            Connecter par clé API
          </button>
        </div>
      </details>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { PaymentProviderCard, PaymentProviderConfigEmits } from '~/types/PaymentProviderConfig'
import type { ComputedRef, EmitFn, Ref } from 'vue'
import type { PaymentAccountStatus, PaymentProviderKind } from '~/services/paymentAccountService'
import { computed, onMounted, ref } from 'vue'
import { PaymentAccountService } from '~/services/paymentAccountService'
import { useToast } from '~/composables/useToast'

/** Connect, tune and disconnect the user's encashment provider (Qonto or Stripe). */

const emit: EmitFn<PaymentProviderConfigEmits> = defineEmits<PaymentProviderConfigEmits>()

const PROVIDER_NAME: Record<PaymentProviderKind, string> = { qonto: 'Qonto', stripe: 'Stripe' }

/** Brand plate behind each wordmark — the providers' own logo colours, white mark on top. */
const PROVIDER_PLATE_CLASS: Record<PaymentProviderKind, string> = {
  qonto: 'bg-[#050505] ring-1 ring-[var(--app-line)]',
  stripe: 'bg-[#635BFF]',
}

/** What each provider brings, in the order the cards are shown. */
const PROVIDER_CARDS: PaymentProviderCard[] = [
  {
    provider: 'qonto',
    role: 'Compte pro & facturation',
    pitch: 'Vos factures sont émises et numérotées depuis votre compte Qonto, puis envoyées avec un lien de paiement.',
    benefits: [
      'Facture officielle à votre nom',
      'Paiement par carte ou par virement',
      'Encaissement sur votre compte pro',
    ],
    caveat: null,
  },
  {
    provider: 'stripe',
    role: 'Encaissement par carte',
    pitch: 'Vos factures et vos paiements passent par votre propre compte Stripe et sa page de paiement hébergée.',
    benefits: [
      'Facture Stripe envoyée au client',
      'Paiement par carte immédiat',
      'Suivi des encaissements dans Stripe',
    ],
    caveat:
      "Stripe n'est pas une plateforme agréée pour la facturation électronique française : à partir de septembre 2027, la conformité de vos factures reste votre responsabilité.",
  },
]

const toast: UseToastReturn = useToast()
const route: ReturnType<typeof useRoute> = useRoute()
const router: ReturnType<typeof useRouter> = useRouter()

const status: Ref<PaymentAccountStatus | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const isBusy: Ref<boolean> = ref(false)
/** Provider whose connection redirect is being prepared, for the per-card spinner. */
const pendingProvider: Ref<PaymentProviderKind | null> = ref(null)
const ibanInput: Ref<string> = ref('')
const apiLoginInput: Ref<string> = ref('')
const apiSecretInput: Ref<string> = ref('')

/** Currently connected provider, or null. */
const connectedProvider: ComputedRef<PaymentProviderKind | null> = computed((): PaymentProviderKind | null =>
  status.value?.is_connected ? (status.value.connected_provider ?? null) : null,
)
const isQonto: ComputedRef<boolean> = computed((): boolean => connectedProvider.value === 'qonto')
const isStripe: ComputedRef<boolean> = computed((): boolean => connectedProvider.value === 'stripe')
const isSandbox: ComputedRef<boolean> = computed((): boolean => status.value?.environment === 'sandbox')

/** Stripe is connected but its hosted onboarding is not finished, so it cannot charge yet. */
const isStripeIncomplete: ComputedRef<boolean> = computed(
  (): boolean => isStripe.value && !status.value?.stripe_charges_enabled,
)

const providerName: ComputedRef<string> = computed((): string => PROVIDER_NAME[connectedProvider.value ?? 'qonto'])
const providerPlateClass: ComputedRef<string> = computed(
  (): string => PROVIDER_PLATE_CLASS[connectedProvider.value ?? 'qonto'],
)

/** Choice cards the user may actually connect (Qonto is gated server-side). */
const availableCards: ComputedRef<PaymentProviderCard[]> = computed((): PaymentProviderCard[] =>
  PROVIDER_CARDS.filter(
    (card: PaymentProviderCard): boolean => card.provider !== 'qonto' || Boolean(status.value?.qonto_available),
  ),
)

/** Footnotes of the shown cards, marked with an asterisk on the card they belong to. */
const caveats: ComputedRef<string[]> = computed((): string[] =>
  availableCards.value
    .map((card: PaymentProviderCard): string | null => card.caveat)
    .filter((caveat: string | null): caveat is string => caveat !== null),
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
 * Redirect to the provider's own connection flow (Qonto OAuth or Stripe hosted onboarding).
 * @param provider - Provider to connect.
 */
async function connectProvider(provider: PaymentProviderKind): Promise<void> {
  isBusy.value = true
  pendingProvider.value = provider
  try {
    window.location.href =
      provider === 'qonto'
        ? await PaymentAccountService.getQontoAuthorizeUrl()
        : await PaymentAccountService.startStripeOnboarding()
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : `Connexion ${PROVIDER_NAME[provider]} impossible`)
    isBusy.value = false
    pendingProvider.value = null
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
