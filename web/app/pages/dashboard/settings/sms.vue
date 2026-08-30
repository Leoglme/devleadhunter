<template>
  <div class="max-w-3xl space-y-6">
    <header>
      <p class="app-label">Réglages</p>
      <h1 class="app-page-title">Relance SMS</h1>
      <p class="text-muted mt-1 text-sm">
        Relancez par SMS les prospects qui n'ont pas réagi à votre email — un rappel vers leur site de démonstration.
        L'envoi respecte les horaires légaux (lun–ven 8h–20h, sam 10h–19h, jamais dimanche ni jour férié), n'inclut que
        les mobiles 06/07, et porte toujours la mention STOP.
      </p>
    </header>

    <section class="app-card p-5">
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Votre expéditeur</h2>
      <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
        Le nom affiché sur le téléphone du prospect (3 à 11 caractères, lettres et chiffres). Les prospects ne peuvent
        pas répondre à un SMS : ils reviennent vers vous depuis le bandeau de leur site de démonstration.
      </p>

      <div
        v-if="!config?.provider_ready"
        class="mt-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3 text-xs text-[var(--app-ink-soft)]"
      >
        Le canal SMS n'est pas encore activé côté serveur (clé smsmode manquante). Vous pouvez déjà régler votre
        expéditeur ; les envois seront possibles une fois la clé configurée.
      </div>

      <div class="mt-4 flex flex-col gap-4 @lg:flex-row @lg:items-end">
        <label class="flex-1">
          <span class="mb-1 block text-xs font-medium text-[var(--app-ink)]">Nom d'expéditeur</span>
          <input v-model="sender" type="text" maxlength="11" placeholder="Dibodev" class="input-field h-10 w-full" />
        </label>
        <div class="flex items-center gap-3">
          <span class="text-xs font-medium text-[var(--app-ink)]">Activer le canal SMS</span>
          <UiSwitch :model-value="enabled" :disabled="isSaving" @update:model-value="enabled = $event" />
        </div>
      </div>

      <div class="mt-4 flex items-center gap-3">
        <button class="app-btn-primary" :disabled="isSaving" @click="save">
          {{ isSaving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
        <span v-if="senderPreview" class="text-xs text-[var(--app-ink-soft)]"> Aperçu : « {{ senderPreview }} » </span>
      </div>
    </section>

    <section class="app-card p-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Prospects à relancer</h2>
          <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
            Emailés il y a plus de 30 jours, sans ouverture ni clic ni réponse, avec un mobile et une démo active.
          </p>
        </div>
        <button
          class="app-btn-secondary"
          :disabled="isLoadingCandidates || rows.length === 0 || !canSend"
          @click="sendAll"
        >
          Tout relancer
        </button>
      </div>

      <div v-if="isLoadingCandidates" class="mt-4 flex justify-center py-6">
        <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-[var(--app-ink-soft)]" />
      </div>

      <p v-else-if="rows.length === 0" class="mt-4 text-xs text-[var(--app-ink-soft)]">
        Aucun prospect éligible à une relance SMS pour le moment.
      </p>

      <div v-else class="mt-4 divide-y divide-[var(--app-line-soft)]">
        <div v-for="row in rows" :key="row.prospect_id" class="flex items-center gap-3 py-2.5">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ row.name }}</p>
            <p class="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-[var(--app-ink-soft)]">
              <span>{{ row.city || '—' }}</span>
              <span class="inline-flex items-center gap-1">
                <UIcon name="i-lucide-phone" class="h-3 w-3" />{{ row.phone }}
              </span>
              <span>Emailé le {{ formatDate(row.emailed_at) }}</span>
            </p>
          </div>
          <span v-if="row.sent" class="app-badge app-badge--success shrink-0">Envoyé</span>
          <span v-else-if="row.error" class="shrink-0 text-xs text-[var(--app-red)]">{{ row.error }}</span>
          <button
            v-else
            class="app-btn-secondary h-8 shrink-0 px-3 text-xs"
            :disabled="row.sending || !canSend"
            @click="sendOne(row)"
          >
            {{ row.sending ? 'Envoi…' : 'Relancer' }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { SmsCandidateRow } from '~/types/SmsSettingsPage'
import type { SmsConfig, SmsRelanceCandidate, SmsSendResult } from '~/services/smsService'
import { SmsService } from '~/services/smsService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const toast: UseToastReturn = useToast()

const config: Ref<SmsConfig | null> = ref(null)
const sender: Ref<string> = ref('')
const enabled: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)

const rows: Ref<SmsCandidateRow[]> = ref([])
const isLoadingCandidates: Ref<boolean> = ref(false)

/** Whether sends are possible (channel enabled + server key ready). */
const canSend: ComputedRef<boolean> = computed(
  (): boolean => Boolean(config.value?.enabled) && Boolean(config.value?.provider_ready),
)

/** Live preview of the sender name as it will appear. */
const senderPreview: ComputedRef<string> = computed((): string => sender.value.trim())

/**
 * Format an ISO date to a short French date.
 * @param iso - The ISO timestamp.
 * @returns The formatted date.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Load the SMS config. */
async function loadConfig(): Promise<void> {
  try {
    config.value = await SmsService.getConfig()
    sender.value = config.value.sender
    enabled.value = config.value.enabled
  } catch {
    toast.error('Impossible de charger la configuration SMS')
  }
}

/** Load the relance candidates. */
async function loadCandidates(): Promise<void> {
  isLoadingCandidates.value = true
  try {
    const candidates: SmsRelanceCandidate[] = await SmsService.listCandidates()
    rows.value = candidates.map(
      (candidate: SmsRelanceCandidate): SmsCandidateRow => ({
        ...candidate,
        sending: false,
        sent: false,
        error: null,
      }),
    )
  } catch {
    rows.value = []
  } finally {
    isLoadingCandidates.value = false
  }
}

/** Save the sender configuration. */
async function save(): Promise<void> {
  isSaving.value = true
  try {
    config.value = await SmsService.updateConfig({ sender: sender.value.trim(), enabled: enabled.value })
    toast.success('Configuration SMS enregistrée')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'enregistrement")
  } finally {
    isSaving.value = false
  }
}

/**
 * Send a relance SMS to one candidate row.
 * @param row - The candidate row.
 */
async function sendOne(row: SmsCandidateRow): Promise<void> {
  row.sending = true
  row.error = null
  try {
    const result: SmsSendResult = await SmsService.sendRelance(row.prospect_id)
    if (result.sent) {
      row.sent = true
    } else {
      row.error = result.reason ?? "Échec de l'envoi"
    }
  } catch (err: unknown) {
    row.error = err instanceof Error ? err.message : "Échec de l'envoi"
  } finally {
    row.sending = false
  }
}

/** Send a relance SMS to every eligible candidate. */
async function sendAll(): Promise<void> {
  for (const row of rows.value) {
    if (!row.sent && !row.error) {
      await sendOne(row)
    }
  }
}

onMounted(async (): Promise<void> => {
  await loadConfig()
  await loadCandidates()
})
</script>
