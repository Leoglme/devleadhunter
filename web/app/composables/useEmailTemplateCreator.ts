import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import type { EmailTemplate } from '~/types'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { EmailTemplatesService } from '~/services/emailTemplatesService'

type IdentifiableTemplate = {
  id: number
}

export type EmailTemplateCreator = {
  openCreate: (assign?: (templateId: number) => void) => void
  openPreview: (templateId: number) => Promise<void>
}

/**
 * Shared create and preview flow for pages hosting `UiTemplateSelect`.
 * @param templates - Caller's reactive template list.
 * @param reload - Reloads that list in place after a template is saved.
 * @returns Handlers to bind to `UiTemplateSelect`'s `@create` and `@preview`.
 */
export function useEmailTemplateCreator<T extends IdentifiableTemplate>(
  templates: Ref<T[]>,
  reload: () => Promise<void>,
): EmailTemplateCreator {
  const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
  const pendingAssign: Ref<((templateId: number) => void) | null> = ref(null)

  /**
   * Open the creation drawer and optionally auto-select the new template id.
   * @param assign - Optional auto-select callback for the new template id.
   */
  function openCreate(assign?: (templateId: number) => void): void {
    pendingAssign.value = assign ?? null
    drawerStack.push({ kind: 'email-template', mode: 'create', template: null })
  }

  /**
   * Open the read-only preview of a template, so the body is visible before picking it.
   * @param templateId - Identifier of the template to preview.
   * @returns A promise resolved once the drawer is pushed.
   */
  async function openPreview(templateId: number): Promise<void> {
    const template: EmailTemplate = await EmailTemplatesService.getEmailTemplate(templateId)
    drawerStack.push({ kind: 'email-template', mode: 'preview', template })
  }

  watch(
    (): number => drawerStack.emailTemplatesRefreshCounter,
    async (): Promise<void> => {
      const previousIds: Set<number> = new Set<number>(templates.value.map((t: T): number => t.id))
      await reload()
      const assign: ((templateId: number) => void) | null = pendingAssign.value
      if (assign) {
        const created: T | undefined = templates.value.find((t: T): boolean => !previousIds.has(t.id))
        if (created) assign(created.id)
        pendingAssign.value = null
      }
    },
  )

  return { openCreate, openPreview }
}
