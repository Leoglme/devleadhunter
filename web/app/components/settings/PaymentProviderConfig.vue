<template>
  <div class="space-y-5">
    <UiLoader v-if="isLoading" />

    <section v-else-if="connectedProvider" class="app-card overflow-hidden">
      <header
        class="flex flex-wrap items-center justify-between gap-3 px-4 py-4 text-white sm:px-5"
        :class="providerBgClass"
        :style="{ backgroundImage: providerGlow }"
      >
        <div class="flex min-w-0 items-center gap-4">
          <UiQontoLogo v-if="isQonto" class="h-5 w-auto shrink-0" role="img" aria-label="Qonto" />
          <UiStripeLogo v-else class="h-6 w-auto shrink-0" role="img" aria-label="Stripe" />
          <div class="min-w-0 border-l border-white/20 pl-4">
            <p
              class="font-[family-name:var(--app-font-mono)] text-[0.66rem] font-medium tracking-[0.12em] text-white/70 uppercase"
            >
              Compte connecté
            </p>
            <p class="mt-0.5 truncate text-sm font-semibold text-white">
              {{ status?.display_name || providerName }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span v-if="isSandbox" :class="BRAND_CHIP_CLASS">Mode test</span>
          <span v-if="isStripeIncomplete" :class="BRAND_CHIP_CLASS">
            <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5" />
            À terminer
          </span>
          <span v-else :class="BRAND_CHIP_CLASS">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Actif
          </span>
        </div>
      </header>

      <div v-if="hasProviderSettings" class="space-y-5 px-4 py-5 sm:px-5">
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
        class="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--app-line)] bg-[var(--app-bg)] px-4 py-3.5 sm:px-5"
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
          class="group flex cursor-pointer flex-col rounded-xl p-4 text-left text-white ring-1 ring-white/10 transition duration-200 focus-visible:ring-2 focus-visible:ring-[var(--app-ink)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--app-bg)] focus-visible:outline-none enabled:hover:shadow-lg enabled:hover:ring-white/35 disabled:cursor-not-allowed disabled:opacity-60 sm:p-5"
          :class="PROVIDER_BG_CLASS[card.provider]"
          :style="{ backgroundImage: PROVIDER_GLOW[card.provider] }"
          :disabled="isBusy"
          @click="connectProvider(card.provider)"
        >
          <span class="flex h-8 items-center">
            <UiQontoLogo
              v-if="card.provider === 'qonto'"
              :class="PROVIDER_LOGO_CLASS[card.provider]"
              role="img"
              aria-label="Qonto"
            />
            <UiStripeLogo v-else :class="PROVIDER_LOGO_CLASS[card.provider]" role="img" aria-label="Stripe" />
          </span>

          <span class="flex flex-1 flex-col">
            <span
              class="mt-5 font-[family-name:var(--app-font-mono)] text-[0.66rem] font-medium tracking-[0.12em] text-white uppercase"
            >
              {{ card.role }}
            </span>
            <span class="mt-2 text-sm leading-relaxed text-white/90">{{ card.pitch }}</span>

            <span class="mt-4 flex flex-col gap-1.5">
              <span v-for="benefit in card.benefits" :key="benefit" class="flex items-start gap-2">
                <UIcon
                  name="i-lucide-check"
                  class="mt-0.5 h-3.5 w-3.5 shrink-0"
                  :class="PROVIDER_CHECK_CLASS[card.provider]"
                />
                <span class="text-xs leading-relaxed text-white">{{ benefit }}</span>
              </span>
            </span>
          </span>

          <span
            class="mt-5 flex items-center justify-between gap-2 border-t border-white/20 pt-4 text-sm font-semibold text-white"
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

/** Brand surface of each provider: Qonto's ink black, Stripe's blurple. */
const PROVIDER_BG_CLASS: Record<PaymentProviderKind, string> = {
  qonto: 'bg-[#050505]',
  stripe: 'bg-[#635BFF]',
}

/**
 * Brand light sweeping the top edge of each card: Qonto's purple, Stripe's
 * magenta-to-amber gradient. Kept in a flat ellipse above the copy so the text
 * always sits on the flat brand colour and keeps its contrast ratio.
 */
const PROVIDER_GLOW: Record<PaymentProviderKind, string> = {
  qonto: 'radial-gradient(130% 68px at 88% 0%, rgba(123, 97, 255, 0.65) 0%, rgba(123, 97, 255, 0) 100%)',
  stripe:
    'radial-gradient(130% 68px at 88% 0%, rgba(255, 178, 94, 0.75) 0%, rgba(226, 80, 190, 0.6) 42%, rgba(99, 91, 255, 0) 100%)',
}

/** Wordmark height per brand, balanced optically (Qonto's mark is wider than Stripe's). */
const PROVIDER_LOGO_CLASS: Record<PaymentProviderKind, string> = {
  qonto: 'h-5 w-auto',
  stripe: 'h-6 w-auto',
}

/** Status pill sitting on a brand surface: dark glass so it holds its contrast over the gradient. */
const BRAND_CHIP_CLASS: string =
  'inline-flex items-center gap-1.5 rounded-full bg-black/40 px-2.5 py-0.5 text-xs font-medium text-white ring-1 ring-white/20'

/** Bullet check colour: Qonto's purple reads on black, white is the only safe accent on blurple. */
const PROVIDER_CHECK_CLASS: Record<PaymentProviderKind, string> = {
  qonto: 'text-[#7B61FF]',
  stripe: 'text-white',
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

/** Whether the connected card has anything to show between its brand header and its footer. */
const hasProviderSettings: ComputedRef<boolean> = computed((): boolean => isQonto.value || isStripeIncomplete.value)

const providerName: ComputedRef<string> = computed((): string => PROVIDER_NAME[connectedProvider.value ?? 'qonto'])
const providerBgClass: ComputedRef<string> = computed(
  (): string => PROVIDER_BG_CLASS[connectedProvider.value ?? 'qonto'],
)
const providerGlow: ComputedRef<string> = computed((): string => PROVIDER_GLOW[connectedProvider.value ?? 'qonto'])

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
