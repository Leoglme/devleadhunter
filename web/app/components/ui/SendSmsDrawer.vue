<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-accent-soft)]"
          >
            <UIcon name="i-lucide-message-square-text" class="h-5 w-5 text-[var(--app-accent-ink)]" />
          </div>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Envoyer un SMS</h2>
            <p v-if="form.to" class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              À {{ form.recipient_name || form.to }}
            </p>
            <p v-else class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">Mobile français (06/07)</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <form id="send-sms-form" class="flex-1 space-y-4 overflow-y-auto px-5 py-4" @submit.prevent="handleSend">
          <div
            v-if="!providerReady"
            class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3 text-xs text-[var(--app-ink-soft)]"
          >
            Le canal SMS n'est pas encore activé côté serveur (clé smsmode manquante). L'envoi échouera tant qu'elle
            n'est pas configurée.
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Numéro mobile <span class="text-[var(--app-red)]">*</span>
            </label>
            <input
              v-model="form.to"
              type="tel"
              required
              class="input-field"
              placeholder="06 12 34 56 78"
              autocomplete="tel"
            />
            <p class="text-muted mt-1 text-[11px]">Uniquement les mobiles français commençant par 06 ou 07.</p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Nom du destinataire</label>
            <input v-model="form.recipient_name" type="text" class="input-field" placeholder="Jean Dupont" />
          </div>

          <div v-if="props.prospect">
            <label class="text-muted mb-1.5 block text-xs font-medium">Modèle</label>
            <UiSelectField
              v-model="selectedTemplateKey"
              :options="templateOptions"
              placeholder="Choisir un modèle…"
              :disabled="isLoadingTemplate"
            />
            <p class="text-muted mt-1 text-[11px]">
              Rempli pour ce prospect avec le lien de sa démo, à retoucher avant l'envoi si besoin.
            </p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Message <span class="text-[var(--app-red)]">*</span>
            </label>
            <textarea
              v-model="form.text"
              required
              rows="6"
              class="input-field resize-none"
              placeholder="Bonjour, je vous ai envoyé un aperçu de site web…"
            />
            <div class="mt-1.5 flex items-center justify-between text-[11px]">
              <span class="text-muted">
                {{ segmentInfo.chars }} caractère{{ segmentInfo.chars > 1 ? 's' : '' }} · {{ segmentInfo.segments }} SMS
                <span v-if="segmentInfo.encoding === 'unicode'" class="text-[var(--app-red)]">
                  · accents/emoji : capacité réduite
                </span>
              </span>
            </div>
            <p v-if="isTooLong" class="mt-1 text-[11px] font-medium text-[var(--app-red)]">
              Message trop long — il partirait en {{ segmentInfo.segments }} SMS. Raccourcissez-le pour tenir en 1 seul.
            </p>
            <p class="text-muted mt-1 text-[11px]">
              La mention « STOP au 36180 » est ajoutée automatiquement (obligatoire).
            </p>
          </div>
        </form>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSending" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="send-sms-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSending || isTooLong"
          >
            <UIcon v-if="isSending" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isSending ? 'Envoi…' : 'Envoyer' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { SendSmsForm, UiSendSmsDrawerEmits, UiSendSmsDrawerProps } from '~/types/UiSendSmsDrawer'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { Prospect } from '~/types'
import type { SendSmsPrefill } from '~/types/DrawerStack'
import type { SelectFieldOption } from '~/types/SelectField'
import type { SmsConfig, SmsSendResult, SmsTemplate, SmsTemplatePreview } from '~/services/smsService'
import { computed, ref, watch } from 'vue'
import { SmsService } from '~/services/smsService'
import { useToast } from '~/composables/useToast'

/** Mandatory STOP mention appended server-side; counted here for an accurate segment preview. */
const STOP_MENTION: string = ' STOP au 36180'

/** GSM-7 basic + extension characters — anything outside forces UCS-2 (unicode) encoding. */
const GSM7_CHARS: string =
  '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà' +
  '^{}\\[~]|€'

/**
 * Closest GSM-7 equivalent for the common non-GSM-7 characters (mirrors the API's `to_gsm7`).
 * The GSM-7 accents (é è à ù…) are kept; the circumflex letters, the lowercase cedilla (ç,
 * absent from GSM-7) and typographic punctuation that would halve the per-SMS budget are
 * simplified, so a normal French message stays one segment.
 */
const GSM7_TRANSLITERATIONS: Record<string, string> = {
  â: 'a',
  ê: 'e',
  î: 'i',
  ô: 'o',
  û: 'u',
  Â: 'A',
  Ê: 'E',
  Î: 'I',
  Ô: 'O',
  Û: 'U',
  ë: 'e',
  ï: 'i',
  Ë: 'E',
  Ï: 'I',
  ÿ: 'y',
  Ÿ: 'Y',
  ç: 'c',
  á: 'a',
  í: 'i',
  ó: 'o',
  ú: 'u',
  ã: 'a',
  õ: 'o',
  Á: 'A',
  Í: 'I',
  Ó: 'O',
  Ú: 'U',
  Ã: 'A',
  Õ: 'O',
  œ: 'oe',
  Œ: 'OE',
  '’': "'",
  '‘': "'",
  '“': '"',
  '”': '"',
  '«': '"',
  '»': '"',
  '–': '-',
  '—': '-',
  '…': '...',
  '•': '-',
  '\u00a0': ' ',
  '\u202f': ' ',
}

/**
 * Simplify the non-GSM-7 characters of a body to their closest GSM-7 equivalent.
 * @param text - The raw message body.
 * @returns The body with circumflex letters and typographic punctuation transliterated.
 */
function normalizeToGsm7(text: string): string {
  let out: string = ''
  for (const char of text) out += GSM7_TRANSLITERATIONS[char] ?? char
  return out
}

const props: UiSendSmsDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospect: {
    type: Object as PropType<Prospect | null>,
    default: null,
  },
  prefill: {
    type: Object as PropType<SendSmsPrefill | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiSendSmsDrawerEmits> = defineEmits<UiSendSmsDrawerEmits>()

const toast: UseToastReturn = useToast()

/** Whether the manual send request is in flight. */
const isSending: Ref<boolean> = ref(false)

/** Whether the platform smsmode key is configured (drives the warning banner). */
const providerReady: Ref<boolean> = ref(true)

/** Key of the recipient the form was last initialised for. */
const lastInitKey: Ref<string> = ref('')

/** Manual send form state. */
const form: Ref<SendSmsForm> = ref({
  to: '',
  recipient_name: '',
  text: '',
})

/** Library templates offered for a linked prospect, as select options. */
const templateOptions: Ref<SelectFieldOption<string>[]> = ref([])

/** Key of the library template the message was filled from (empty = free text). */
const selectedTemplateKey: Ref<string> = ref('')

/** Whether a template is being rendered for the prospect. */
const isLoadingTemplate: Ref<boolean> = ref(false)

/**
 * Live character + segment estimate of the full body (message + STOP mention), counted on the
 * GSM-7-normalized text so the preview matches what the API actually sends.
 */
const segmentInfo: ComputedRef<{ chars: number; segments: number; encoding: 'gsm' | 'unicode' }> = computed(() => {
  const trimmed: string = normalizeToGsm7(form.value.text.trim())
  if (!trimmed) {
    return { chars: 0, segments: 0, encoding: 'gsm' }
  }
  const body: string = trimmed.includes('36180') ? trimmed : trimmed + STOP_MENTION
  const isUnicode: boolean = [...body].some((char: string): boolean => !GSM7_CHARS.includes(char))
  const chars: number = body.length
  const single: number = isUnicode ? 70 : 160
  const multi: number = isUnicode ? 67 : 153
  const segments: number = chars <= single ? 1 : Math.ceil(chars / multi)
  return { chars, segments, encoding: isUnicode ? 'unicode' : 'gsm' }
})

/** A message that would bill (and send) more than one SMS is blocked. */
const isTooLong: ComputedRef<boolean> = computed((): boolean => segmentInfo.value.segments > 1)

/**
 * Load the SMS config to know whether the server key is ready.
 * @returns A promise that resolves once loaded.
 */
async function loadConfig(): Promise<void> {
  try {
    const config: SmsConfig = await SmsService.getConfig()
    providerReady.value = config.provider_ready
  } catch {
    providerReady.value = true
  }
}

/**
 * Load the first-contact templates offered for a linked prospect.
 * @returns A promise that resolves once the options are set.
 */
async function loadTemplates(): Promise<void> {
  if (!props.prospect) return
  try {
    const templates: SmsTemplate[] = await SmsService.listTemplates('first_contact')
    templateOptions.value = templates.map(
      (template: SmsTemplate): SelectFieldOption<string> => ({ value: template.key, label: template.name }),
    )
  } catch {
    templateOptions.value = []
  }
}

/**
 * Fill the message with a template rendered for the linked prospect (editable afterwards).
 * @param key - The chosen template key.
 * @returns A promise that resolves once the message is filled.
 */
async function applyTemplate(key: string): Promise<void> {
  if (!key || !props.prospect) return
  isLoadingTemplate.value = true
  try {
    const preview: SmsTemplatePreview = await SmsService.previewTemplate(key, props.prospect.id)
    form.value.text = preview.body
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de préparer ce modèle pour ce prospect')
    selectedTemplateKey.value = ''
  } finally {
    isLoadingTemplate.value = false
  }
}

/**
 * Send the SMS through the manual endpoint, then notify the host so the stack can navigate back.
 * @returns A promise that resolves once the SMS has been dispatched.
 */
async function handleSend(): Promise<void> {
  if (isTooLong.value) {
    toast.error('Message trop long : il tient sur plusieurs SMS. Raccourcissez-le.')
    return
  }
  isSending.value = true
  try {
    const result: SmsSendResult = await SmsService.sendManual({
      to: form.value.to,
      text: form.value.text,
      prospect_id: props.prospect?.id ?? null,
      recipient_name: form.value.recipient_name || null,
    })
    if (result.sent) {
      toast.success('SMS envoyé')
      emit('sent')
    } else {
      toast.error(result.reason ?? "Échec de l'envoi du SMS")
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi du SMS")
  } finally {
    isSending.value = false
  }
}

watch(
  (): [boolean, number | undefined, SendSmsPrefill | null] => [props.open, props.prospect?.id, props.prefill ?? null],
  ([open]: [boolean, number | undefined, SendSmsPrefill | null]): void => {
    if (!open) return
    void loadConfig()
    // Only when the recipient changes: returning from a stacked drawer must not wipe the draft.
    const key: string = props.prefill
      ? `prefill:${props.prefill.to}|${props.prefill.text}`
      : `prospect:${props.prospect?.id ?? 'blank'}`
    if (key === lastInitKey.value) return
    lastInitKey.value = key
    selectedTemplateKey.value = ''
    templateOptions.value = []
    if (props.prefill) {
      form.value = { ...props.prefill }
      return
    }
    form.value = {
      to: props.prospect?.phone ?? '',
      recipient_name: props.prospect?.name ?? '',
      text: '',
    }
    loadTemplates()
  },
  { immediate: true },
)

watch(selectedTemplateKey, applyTemplate)
</script>

<style scoped>
/* Panel slide from right */
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
