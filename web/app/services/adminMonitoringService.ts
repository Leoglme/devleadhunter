import { ApiClient } from './api'

/**
 * Admin monitoring service — reads the reactive scraping diagnostics (source health,
 * incidents, captured HTML) exposed by the admin-only API.
 * @module services/adminMonitoringService
 */

/** Health summary for one scraping source over the last 24 h. */
export type ScraperSourceHealth = {
  source: string
  latest_status: string
  latest_at: string | null
  runs_24h: number
  incidents_24h: number
  last_ok_at: string | null
  latest_incident_id: number | null
}

/** System + scraping health overview. */
export type MonitoringOverview = {
  database: string
  diagnostics_total: number
  activity_total: number
  sources: ScraperSourceHealth[]
}

/** One logged action in the activity feed. */
export type ActivityLogEntry = {
  id: number
  category: string
  action: string
  status: string
  title: string
  detail: string | null
  entity_type: string | null
  entity_id: number | null
  created_at: string | null
}

/** A page of the activity feed, with the distinct categories present (for the filter). */
export type ActivityLogResponse = {
  categories: string[]
  items: ActivityLogEntry[]
}

/** Filters applied to the activity feed query. */
export type ActivityLogFilters = {
  limit?: number
  status?: string
  category?: string
  q?: string
}

/** One recorded source-run outcome. */
export type ScraperIncident = {
  id: number
  source: string
  status: string
  category: string | null
  city: string | null
  results_count: number
  expected_count: number | null
  error_message: string | null
  has_html: boolean
  created_at: string | null
}

export class AdminMonitoringService {
  /**
   * Fetch the system + per-source scraping health overview.
   * @returns The monitoring overview.
   */
  static async getMonitoringOverview(): Promise<MonitoringOverview> {
    return ApiClient.get<MonitoringOverview>('/api/v1/admin/monitoring/overview')
  }

  /**
   * Fetch recent scraper incidents (per-source run outcomes).
   * @param limit - Maximum rows (1-500).
   * @param source - Optional source filter.
   * @returns The incident list.
   */
  static async getScraperIncidents(limit: number = 100, source?: string): Promise<{ items: ScraperIncident[] }> {
    return ApiClient.get<{ items: ScraperIncident[] }>('/api/v1/admin/monitoring/scrapers/incidents', {
      params: { limit, source: source ?? undefined },
    })
  }

  /**
   * Fetch the raw HTML captured for a blocked-source incident (as plain text).
   * @param incidentId - The diagnostic id.
   * @returns The captured HTML markup.
   */
  static async getScraperIncidentHtml(incidentId: number): Promise<string> {
    return ApiClient.get<string>(`/api/v1/admin/monitoring/scrapers/incidents/${incidentId}/html`)
  }

  /**
   * Fetch the activity feed, filtered by status / category / free text.
   * @param filters - The active filters (all optional; empty strings are dropped).
   * @returns The matching entries and the distinct categories present.
   */
  static async getActivityLog(filters: ActivityLogFilters = {}): Promise<ActivityLogResponse> {
    return ApiClient.get<ActivityLogResponse>('/api/v1/admin/monitoring/activity', {
      params: {
        limit: filters.limit ?? 500,
        status: filters.status || undefined,
        category: filters.category || undefined,
        q: filters.q?.trim() || undefined,
      },
    })
  }
}
