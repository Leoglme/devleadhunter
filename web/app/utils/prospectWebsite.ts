import type { Prospect } from '~/types'

/** Reading rules for a prospect's website — a dead or directory site counts as "no real website". */
export class ProspectWebsite {
  private constructor() {}

  /**
   * Whether the prospect has a website that actually responds (not dead, not a directory mini-site).
   * @param prospect - Prospect to evaluate.
   * @returns True when the found website is a real, live one.
   */
  static hasWorkingWebsite(prospect: Prospect): boolean {
    return !!prospect.website && prospect.website_status !== 'dead' && prospect.website_status !== 'placeholder'
  }

  /**
   * Whether a URL was found but points to a dead site or a directory mini-site.
   * @param prospect - Prospect to evaluate.
   * @returns True for the best outreach targets: the prospect already paid for a website once.
   */
  static hasBrokenWebsite(prospect: Prospect): boolean {
    return !!prospect.website && (prospect.website_status === 'dead' || prospect.website_status === 'placeholder')
  }
}
