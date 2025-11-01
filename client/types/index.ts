/**
 * Shared TypeScript types and interfaces for the application
 * @module types
 */

/**
 * Business category for prospect search
 */
export type BusinessCategory = 
  | 'restaurant' 
  | 'plombier' 
  | 'electricien' 
  | 'coiffeur' 
  | 'garage' 
  | 'all';

/**
 * Source of prospect data
 */
export type ProspectSource = 
  | 'google' 
  | 'pagesjaunes' 
  | 'yelp' 
  | 'osm' 
  | 'mappy'
  | 'mock'
  | 'all';

/**
 * Prospect interface representing a business without website
 */
export interface Prospect {
  /** Unique identifier for the prospect */
  id: string;
  /** Business name */
  name: string;
  /** Street address */
  address?: string;
  /** City */
  city?: string;
  /** Phone number */
  phone?: string;
  /** Email address (if available) */
  email?: string;
  /** Website URL (if available) */
  website?: string;
  /** Business category */
  category: string;
  /** Source of the prospect data */
  source: ProspectSource;
  /** Confidence score (1-4) */
  confidence: number;
  /** Timestamp of when prospect was found */
  createdAt?: string;
}

/**
 * Search filters for prospect search
 */
export interface ProspectSearchFilters {
  /** Business category filter */
  category?: BusinessCategory;
  /** City filter */
  city?: string;
  /** Source filter */
  source?: ProspectSource;
  /** Maximum number of results */
  maxResults?: number;
}

/**
 * Campaign interface for bulk email sending
 */
export interface Campaign {
  /** Unique identifier for the campaign */
  id: string;
  /** Campaign name */
  name: string;
  /** Campaign description */
  description: string;
  /** List of prospect IDs in the campaign */
  prospectIds: string[];
  /** Campaign status */
  status: 'draft' | 'active' | 'completed';
  /** Timestamp of creation */
  createdAt: string;
  /** Timestamp of last update */
  updatedAt: string;
}

/**
 * User role enumeration
 */
export type UserRole = 'USER' | 'ADMIN';

/**
 * User interface
 */
export interface User {
  /** Unique identifier for the user */
  id: number;
  /** User name */
  name: string;
  /** User email */
  email: string;
  /** User role */
  role: UserRole;
  /** Whether user is active */
  is_active: boolean;
  /** Timestamp of account creation */
  created_at: string;
  /** Timestamp of last update */
  updated_at: string | null;
}

/**
 * Login credentials
 */
export interface LoginCredentials {
  /** User email */
  email: string;
  /** User password */
  password: string;
}

/**
 * Signup data
 */
export interface SignupData {
  /** User name */
  name: string;
  /** User email */
  email: string;
  /** User password */
  password: string;
}

/**
 * API Response wrapper
 */
export interface ApiResponse<T> {
  /** Response data */
  data: T;
  /** Success status */
  success: boolean;
  /** Error message (if any) */
  message?: string;
}

/**
 * Auth token response
 */
export interface TokenResponse {
  /** JWT access token */
  access_token: string;
  /** Token type */
  token_type: string;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  /** List of items */
  items: T[];
  /** Total number of items */
  total: number;
  /** Current page */
  page: number;
  /** Items per page */
  perPage: number;
  /** Total number of pages */
  totalPages: number;
}

/**
 * Email sending data
 */
export interface EmailData {
  /** Recipient email */
  to: string;
  /** Email subject */
  subject: string;
  /** Email body */
  body: string;
  /** Prospect ID (optional) */
  prospectId?: string;
}

/**
 * Bulk email sending data
 */
export interface BulkEmailData {
  /** Campaign ID */
  campaignId: string;
  /** Email subject */
  subject: string;
  /** Email body */
  body: string;
}


