import type { SiteContent } from '@devleadhunter/website-content'

/** A Storyblok blok object: arbitrary content fields plus `component` / `_uid`. */
type Blok = Record<string, unknown>

/**
 * Bridge between the Storyblok-native `site_content` blok tree and the flat `SiteContent`
 * the template layers consume.
 *
 * The DB `content_json` fallback is already flat, so this only runs when demo-host resolves
 * the Storyblok story itself (live Visual Editor or preview draft).
 */
export class StoryblokSiteContentBridge {
  /**
   * Read a Storyblok text field.
   *
   * @param value - Raw field value.
   * @returns The string, or undefined when it is empty or not a string.
   */
  private static readString(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim() ? value : undefined
  }

  /**
   * Read a Storyblok asset field, which arrives as an object carrying a `filename`.
   *
   * @param value - Raw field value (asset object, or a bare URL string from the `content_json` fallback / pre-asset era).
   * @returns The image URL, or undefined when empty.
   */
  private static readAsset(value: unknown): string | undefined {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return this.readString((value as Blok).filename)
    }
    return this.readString(value)
  }

  /**
   * Read a Storyblok `number` field, which comes back as a numeric string.
   *
   * @param value - Raw field value (number or numeric string).
   * @returns The parsed number, or undefined when empty or not numeric.
   */
  private static readNumber(value: unknown): number | undefined {
    if (typeof value === 'number') {
      return value
    }
    if (typeof value === 'string' && value.trim()) {
      const parsed: number = Number(value)
      return Number.isNaN(parsed) ? undefined : parsed
    }
    return undefined
  }

  /**
   * Read a repeatable blok field.
   *
   * @param value - Raw field value.
   * @returns The bloks, or an empty array when the field is absent.
   */
  private static readBlokList(value: unknown): Blok[] {
    return Array.isArray(value) ? (value as Blok[]) : []
  }

  /**
   * Read an object field.
   *
   * @param value - Raw field value.
   * @returns The object, or an empty object when the field is absent or is an array.
   */
  private static readBlok(value: unknown): Blok {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Blok) : {}
  }

  /**
   * Read a single-blok field, which Storyblok returns as a LIST once the story has been
   * republished from the editor even though our API writes it as a plain object.
   *
   * @param value - Raw field value (object or one-element list).
   * @returns The blok, or an empty object.
   */
  private static readSingleBlok(value: unknown): Blok {
    return Array.isArray(value) ? this.readBlok(value[0]) : this.readBlok(value)
  }

  /**
   * Tell whether a component name is one of ours: the section bloks or the legacy single blok.
   *
   * @param component - A blok's `component` value.
   * @returns Whether it is a `section_*` blok or the legacy `site_content` blok.
   */
  private static isContentBlok(component: unknown): boolean {
    return component === 'site_content' || (typeof component === 'string' && component.startsWith('section_'))
  }

  /**
   * Merge the section bloks' fields into one flat blok (keys are unique across sections).
   *
   * Accepts the sectioned page (`body: [section_hero, … ]`), a bare section, or the legacy single
   * `site_content` blok, page-wrapped or not.
   *
   * @param raw - Resolved content (content_json, Storyblok draft, or live bridge edits).
   * @returns The merged fields, or undefined when no content blok is present.
   */
  private static collectContentFields(raw: Blok): Blok | undefined {
    const blocks: Blok[] = this.isContentBlok(raw?.component)
      ? [raw]
      : this.readBlokList(raw.body).filter((blok: Blok): boolean => this.isContentBlok(blok?.component))
    if (blocks.length === 0) {
      return undefined
    }
    const merged: Blok = {}
    blocks.forEach((blok: Blok): void => {
      Object.keys(blok).forEach((key: string): void => {
        if (key !== '_uid' && key !== 'component') {
          merged[key] = blok[key]
        }
      })
    })
    return merged
  }

  /**
   * Tell whether a resolved content object is the Storyblok-native representation rather than flat `SiteContent`.
   *
   * @param raw - Resolved content object.
   * @returns Whether the content carries our section (or legacy) bloks.
   */
  static isStoryblokSiteContent(raw: Record<string, unknown>): boolean {
    return this.collectContentFields(raw as Blok) !== undefined
  }

  /**
   * Flatten the Storyblok-native representation into the `SiteContent` a template layer renders.
   *
   * The section bloks are merged, nested blok lists lose their `_uid` / `component`, the palette is
   * read from the page `theme` field, and asset fields are flattened back to their image URL (`filename`).
   *
   * @param raw - Resolved content (page-wrapped or bare `site_content` blok).
   * @returns A flat `SiteContent` — absent keys mean hidden sections.
   */
  static toSiteContent(raw: Record<string, unknown>): SiteContent {
    const blok: Blok = this.collectContentFields(raw as Blok) ?? {}
    // Palette lives on the page `theme` field now; fall back to a legacy in-content palette.
    const themePalette: Blok = this.readSingleBlok((raw as Blok).theme)
    const palette: Blok = Object.keys(themePalette).length > 0 ? themePalette : this.readSingleBlok(blok.palette)

    return {
      businessName: this.readString(blok.businessName),
      phone: this.readString(blok.phone),
      email: this.readString(blok.email),
      city: this.readString(blok.city),
      area: this.readString(blok.area),
      subtitle: this.readString(blok.subtitle),
      about: this.readString(blok.about),
      heroBadge: this.readString(blok.heroBadge),
      heroPoints: this.readBlokList(blok.heroPoints)
        .map((item: Blok): string | undefined => this.readString(item.text))
        .filter((text: string | undefined): text is string => Boolean(text)),
      ctaCallLabel: this.readString(blok.ctaCallLabel),
      ctaQuoteLabel: this.readString(blok.ctaQuoteLabel),
      trustItems: this.readBlokList(blok.trustItems)
        .map((item: Blok): { value?: string; label?: string } => ({
          value: this.readString(item.value),
          label: this.readString(item.label),
        }))
        .filter((item: Blok): boolean => Boolean(item.value) || Boolean(item.label)),
      servicesHeading: this.readString(blok.servicesHeading),
      galleryHeading: this.readString(blok.galleryHeading),
      reviewsHeading: this.readString(blok.reviewsHeading),
      faqHeading: this.readString(blok.faqHeading),
      aboutHeading: this.readString(blok.aboutHeading),
      contactHeading: this.readString(blok.contactHeading),
      logo: this.readAsset(blok.logo),
      heroImage: this.readAsset(blok.heroImage),
      aboutImage: this.readAsset(blok.aboutImage),
      palette: {
        primary: this.readString(palette.primary),
        secondary: this.readString(palette.secondary),
        accent: this.readString(palette.accent),
      },
      gallery: this.readBlokList(blok.gallery)
        .map((item: Blok): { url?: string; alt?: string } => ({
          url: this.readAsset(item),
          alt: this.readString(item.alt),
        }))
        .filter((image: Blok): boolean => Boolean(image.url)),
      services: this.readBlokList(blok.services).map((item: Blok): { title?: string; description?: string } => ({
        title: this.readString(item.title),
        description: this.readString(item.description),
      })),
      reviews: this.readBlokList(blok.reviews).map(
        (item: Blok): { author?: string; rating?: number; text?: string } => ({
          author: this.readString(item.author),
          rating: this.readNumber(item.rating),
          text: this.readString(item.text),
        }),
      ),
      faq: this.readBlokList(blok.faq).map((item: Blok): { question?: string; answer?: string } => ({
        question: this.readString(item.question),
        answer: this.readString(item.answer),
      })),
      openingHours: this.readBlokList(blok.openingHours)
        .map((item: Blok): { day?: string; hours?: string } => ({
          day: this.readString(item.day),
          hours: this.readString(item.hours),
        }))
        .filter((entry: Blok): boolean => Boolean(entry.day) || Boolean(entry.hours)),
      beforeAfter: this.readBlokList(blok.beforeAfter)
        .map((item: Blok): { before?: string; after?: string; label?: string } => ({
          before: this.readAsset(item.before),
          after: this.readAsset(item.after),
          label: this.readString(item.label),
        }))
        .filter((pair: Blok): boolean => Boolean(pair.before) || Boolean(pair.after)),
      social: this.readBlokList(blok.social)
        .map((item: Blok): { network?: string; url?: string } => ({
          network: this.readString(item.network),
          url: this.readString(item.url),
        }))
        .filter((link: Blok): boolean => Boolean(link.url)),
    }
  }
}
