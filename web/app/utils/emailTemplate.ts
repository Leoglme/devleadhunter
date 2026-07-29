import type { EmailTemplate, EmailTemplateCategory } from '~/types'

/** Sequence steps a template can belong to, in the order the tabs display them. */
export const EMAIL_TEMPLATE_CATEGORIES: EmailTemplateCategory[] = ['first_email', 'follow_up']

/** Human label of each sequence step. */
export const EMAIL_TEMPLATE_CATEGORY_LABELS: Record<EmailTemplateCategory, string> = {
  first_email: 'Premier email',
  follow_up: 'Relance',
}

/** One-line explanation of each sequence step, shown as the tab hint. */
export const EMAIL_TEMPLATE_CATEGORY_HINTS: Record<EmailTemplateCategory, string> = {
  first_email: 'Le mail qui ouvre la séquence',
  follow_up: 'Les mails qui relancent ensuite',
}

/**
 * Whether a template is one of the recommended picks, pinned at the top of its tab.
 * @param template - Template to test.
 * @returns True when the template carries a pinning weight.
 */
export function isTemplateRecommended(template: EmailTemplate): boolean {
  return (template.sort_order ?? 0) > 0
}

/**
 * Template name without its leading « ★ », which the seeded names embed as text.
 * The app renders that star itself, in the accent colour, so keeping it in the
 * string would show it twice.
 * @param name - Raw template name.
 * @returns The name stripped of a leading star and its spacing.
 */
export function templateNameWithoutStar(name: string): string {
  return name.replace(/^\s*★\s*/, '')
}
