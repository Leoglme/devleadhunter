<template>
  <div>
    <UiProspectDrawer
      :open="prospectEntry !== null"
      :prospect="prospectEntry?.prospect ?? null"
      :start-in-edit="prospectEntry?.startInEdit ?? false"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="handleProspectUpdated"
      @deleted="handleProspectDeleted"
      @send-email="handleSendEmail"
      @mark-as-sold="handleMarkAsSold"
      @toggle-contacted="handleToggleContacted"
    />

    <UiSendEmailDrawer
      :open="sendEmailEntry !== null"
      :prospect="sendEmailEntry?.prospect ?? null"
      :prefill="sendEmailEntry?.prefill ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @sent="handleEmailSent"
    />

    <UiEmailLogDrawer
      :open="emailLogEntry !== null"
      :log="emailLogEntry?.log ?? null"
      :campaign-name="emailLogEntry?.campaignName"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @resend="handleResendEmail"
    />

    <UiEmailTemplateDrawer
      :open="emailTemplateEntry !== null"
      :mode="emailTemplateEntry?.mode ?? 'create'"
      :template="emailTemplateEntry?.template ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleTemplateSaved"
      @edit="handleTemplateEdit"
    />

    <UiEmailSignaturesDrawer
      :open="emailSignaturesEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiProfileDrawer
      :open="profileEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiOrganizationDrawer
      :open="organizationEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCampaignDrawer
      :open="campaignFormEntry !== null"
      :mode="campaignFormEntry?.mode ?? 'create'"
      :campaign="campaignFormEntry?.campaign ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleCampaignSaved"
    />

    <UiAddProspectDrawer
      :open="addProspectEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @created="handleProspectCreated"
    />

    <UiSearchProspectsDrawer
      :open="searchProspectsEntry !== null"
      :show-back="hasPrevious"
      :prefill="searchProspectsEntry?.prefill ?? null"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiSendPolicyDrawer
      :open="sendPolicyEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCoverageFiltersDrawer
      :open="coverageFiltersEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCoverageProspectsDrawer
      :open="coverageProspectsEntry !== null"
      :show-back="hasPrevious"
      :zone="coverageProspectsEntry?.zone ?? null"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiOrderDrawer
      :open="orderEntry !== null"
      :order="orderEntry?.order ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="drawerStack.notifyOrderUpdated"
      @deleted="handleOrderDeleted"
      @finalize="handleFinalizeSale"
    />

    <UiFinalizeSaleDrawer
      :open="finalizeSaleEntry !== null"
      :order="finalizeSaleEntry?.order ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="drawerStack.notifyOrderUpdated"
    />

    <UiUserFormDrawer
      :open="userFormEntry !== null"
      :mode="userFormEntry?.mode ?? 'create'"
      :user="userFormEntry?.user ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleUserSaved"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef } from 'vue'
import type {
  AddProspectDrawerEntry,
  CoverageFiltersDrawerEntry,
  CoverageProspectsDrawerEntry,
  CampaignFormDrawerEntry,
  EmailLogDrawerEntry,
  EmailSignaturesDrawerEntry,
  EmailTemplateDrawerEntry,
  FinalizeSaleDrawerEntry,
  OrderDrawerEntry,
  OrganizationDrawerEntry,
  ProfileDrawerEntry,
  ProspectDrawerEntry,
  SearchProspectsDrawerEntry,
  SendEmailDrawerEntry,
  SendPolicyDrawerEntry,
  UserFormDrawerEntry,
} from '~/types/DrawerStack'
import type { EmailTemplate, Prospect } from '~/types'
import type { Order } from '~/services/ordersService'
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { ProspectsService } from '~/services/prospectsService'
import { OrdersService } from '~/services/ordersService'
import { useToast } from '~/composables/useToast'

const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const toast: UseToastReturn = useToast()

/** Top entry narrowed to the prospect drawer (null when another kind is on top). */
const prospectEntry: ComputedRef<ProspectDrawerEntry | null> = computed((): ProspectDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'prospect' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the send-email drawer. */
const sendEmailEntry: ComputedRef<SendEmailDrawerEntry | null> = computed((): SendEmailDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'send-email' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the email-log drawer. */
const emailLogEntry: ComputedRef<EmailLogDrawerEntry | null> = computed((): EmailLogDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'email-log' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the email-template drawer. */
const emailTemplateEntry: ComputedRef<EmailTemplateDrawerEntry | null> = computed(
  (): EmailTemplateDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'email-template' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the email-signatures drawer. */
const emailSignaturesEntry: ComputedRef<EmailSignaturesDrawerEntry | null> = computed(
  (): EmailSignaturesDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'email-signatures' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the profile drawer. */
const profileEntry: ComputedRef<ProfileDrawerEntry | null> = computed((): ProfileDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'profile' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the organization drawer. */
const organizationEntry: ComputedRef<OrganizationDrawerEntry | null> = computed((): OrganizationDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'organization' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the campaign create/edit drawer. */
const campaignFormEntry: ComputedRef<CampaignFormDrawerEntry | null> = computed((): CampaignFormDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'campaign-form' ? drawerStack.topEntry : null
})

/** Campaign renamed from its drawer — refresh the page behind, then leave the stack. */
function handleCampaignSaved(): void {
  drawerStack.bumpCampaignsRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Top entry narrowed to the manual prospect creation drawer. */
const addProspectEntry: ComputedRef<AddProspectDrawerEntry | null> = computed((): AddProspectDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'add-prospect' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the prospect search drawer. */
const searchProspectsEntry: ComputedRef<SearchProspectsDrawerEntry | null> = computed(
  (): SearchProspectsDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'search-prospects' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the send-policy drawer. */
const sendPolicyEntry: ComputedRef<SendPolicyDrawerEntry | null> = computed((): SendPolicyDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'send-policy' ? drawerStack.topEntry : null
})

/** Coverage-map filters entry when it is the top of the stack. */
const coverageFiltersEntry: ComputedRef<CoverageFiltersDrawerEntry | null> = computed(
  (): CoverageFiltersDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'coverage-filters' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the order drawer. */
const orderEntry: ComputedRef<OrderDrawerEntry | null> = computed((): OrderDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'order' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the sale finalization drawer. */
const finalizeSaleEntry: ComputedRef<FinalizeSaleDrawerEntry | null> = computed((): FinalizeSaleDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'finalize-sale' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the user create/edit drawer. */
const userFormEntry: ComputedRef<UserFormDrawerEntry | null> = computed((): UserFormDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'user-form' ? drawerStack.topEntry : null
})

/** User saved from its drawer — refresh the list page, then leave the stack. */
function handleUserSaved(): void {
  drawerStack.bumpUsersRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Stack the sale finalization on top of the order drawer. */
function handleFinalizeSale(): void {
  const entry: OrderDrawerEntry | null = orderEntry.value
  if (entry) drawerStack.push({ kind: 'finalize-sale', order: entry.order })
}

/**
 * Order deleted from its drawer — drop it from the stack and close.
 * @param orderId - Identifier of the deleted order.
 */
function handleOrderDeleted(orderId: number): void {
  drawerStack.notifyOrderDeleted(orderId)
  drawerStack.closeAll()
}

/** Coverage-map zone prospects entry when it is the top of the stack. */
const coverageProspectsEntry: ComputedRef<CoverageProspectsDrawerEntry | null> = computed(
  (): CoverageProspectsDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'coverage-prospects' ? drawerStack.topEntry : null
  },
)

/**
 * Prospect created from the add drawer — notify pages (list insert) and chain
 * straight to the new prospect's detail drawer.
 * @param created - The freshly created prospect.
 */
function handleProspectCreated(created: Prospect): void {
  drawerStack.notifyProspectUpdated(created)
  drawerStack.push({ kind: 'prospect', prospect: created })
}

/** Whether the back affordance should be visible on the top drawer. */
const hasPrevious: ComputedRef<boolean> = computed((): boolean => drawerStack.hasPrevious)

/**
 * Prospect edited from the drawer — refresh the stack and notify pages.
 * @param updated - The freshly updated prospect.
 */
function handleProspectUpdated(updated: Prospect): void {
  drawerStack.notifyProspectUpdated(updated)
}

/**
 * Prospect deleted from its drawer — drop it from the stack and notify pages.
 * @param prospectId - Identifier of the deleted prospect.
 */
function handleProspectDeleted(prospectId: number): void {
  drawerStack.notifyProspectDeleted(prospectId)
}

/**
 * « Email » action — stack the composer on top of the prospect drawer.
 * @param prospect - The prospect used to prefill the composer.
 */
function handleSendEmail(prospect: Prospect): void {
  drawerStack.push({ kind: 'send-email', prospect })
}

/**
 * « Marquer comme vendu » action — create the order then open the sales page.
 * @param prospect - The prospect being marked as sold.
 */
async function handleMarkAsSold(prospect: Prospect): Promise<void> {
  try {
    const order: Order = await OrdersService.createOrder({
      product_type: 'website',
      prospect_id: prospect.id,
      business_name: prospect.name,
      customer_email: prospect.email ?? null,
    })
    toast.success(`Vente créée pour « ${prospect.name} »`)
    drawerStack.push({ kind: 'order', order })
    navigateTo('/dashboard/orders')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la création de la vente')
  }
}

/**
 * Contacted toggle from the prospect drawer — persist and broadcast.
 * @param prospect - The prospect whose contacted status was toggled.
 */
async function handleToggleContacted(prospect: Prospect): Promise<void> {
  const next: boolean = !prospect.contacted
  try {
    const updated: Prospect = await ProspectsService.updateProspect(prospect.id, { contacted: next })
    drawerStack.notifyProspectUpdated(updated)
    toast.success(next ? `« ${prospect.name} » marqué comme contacté` : `« ${prospect.name} » remis en non contacté`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  }
}

/**
 * Convert an HTML email body to editable plain text (paragraph/line breaks
 * preserved, tags stripped).
 * @param html - HTML body from the email log (may be null).
 * @returns Plain-text version, or an empty string.
 */
function htmlToPlainText(html: string | null | undefined): string {
  if (!html) return ''
  const withBreaks: string = html.replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n\n')
  const doc: Document = new DOMParser().parseFromString(withBreaks, 'text/html')
  return (doc.body.textContent ?? '').replace(/\n{3,}/g, '\n\n').trim()
}

/** Stack email composer prefilled from the log row (resend). */
function handleResendEmail(): void {
  const entry: EmailLogDrawerEntry | null = emailLogEntry.value
  if (!entry) return
  drawerStack.push({
    kind: 'send-email',
    prospect: null,
    prefill: {
      recipient_email: entry.log.recipient_email,
      recipient_name: entry.log.recipient_name ?? '',
      subject: entry.log.subject,
      body: htmlToPlainText(entry.log.body_html),
    },
  })
}

/** Refresh logs after send; back or close the stack. */
function handleEmailSent(): void {
  drawerStack.bumpEmailLogsRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Refresh templates after save; back or close the stack. */
function handleTemplateSaved(): void {
  drawerStack.bumpEmailTemplatesRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/**
 * Switch the template drawer from preview to edit (same kind → replaces top).
 * @param template - Template to edit.
 */
function handleTemplateEdit(template: EmailTemplate): void {
  drawerStack.push({ kind: 'email-template', mode: 'edit', template })
}

/**
 * Escape closes the top drawer (revealing the previous stacked one, if any).
 * Skips events already consumed (e.g. by the command palette).
 * @param event - Keyboard event.
 */
function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && !event.defaultPrevented && drawerStack.topEntry) {
    drawerStack.back()
  }
}

onMounted((): void => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount((): void => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>
