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
  /** Credit balance (-1 for unlimited/admin) */
  credit_balance?: number | null;
  /** Credits available (-1 for unlimited/admin) */
  credits_available?: number | null;
  /** Credits consumed */
  credits_consumed?: number | null;
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

/**
 * Credit settings interface for credit system configuration
 */
export interface CreditSettings {
  /** Unique identifier for the settings (always 1) */
  id: number;
  /** Price of one credit in EUR */
  price_per_credit: number;
  /** Number of credits required for a search operation */
  credits_per_search: number;
  /** Number of credits required per prospect found */
  credits_per_result: number;
  /** Number of credits required per email sent */
  credits_per_email: number;
  /** Number of free credits given on user registration */
  free_credits_on_signup: number;
  /** Minimum number of credits that can be purchased */
  minimum_credits_purchase: number;
  /** Timestamp when settings were created */
  created_at: string;
  /** Timestamp when settings were last updated */
  updated_at: string | null;
}

/**
 * Checkout session creation request
 */
export interface CheckoutSessionCreate {
  /** Number of credits to purchase */
  credits: number;
  /** URL to redirect after successful payment (optional) */
  success_url?: string;
  /** URL to redirect if payment is cancelled (optional) */
  cancel_url?: string;
}

/**
 * Checkout session response
 */
export interface CheckoutSessionResponse {
  /** Stripe checkout session ID */
  session_id: string;
  /** Stripe checkout session URL */
  url: string;
  /** Payment amount in cents */
  amount: number;
  /** Number of credits being purchased */
  credits: number;
}

/**
 * Credit transaction type
 */
export type CreditTransactionType = 'PURCHASE' | 'USAGE' | 'REFUND' | 'FREE_GIFT';

/**
 * Credit transaction interface
 */
export interface CreditTransaction {
  /** Transaction unique identifier */
  id: number;
  /** User ID who owns this transaction */
  user_id: number;
  /** Transaction type */
  transaction_type: CreditTransactionType;
  /** Number of credits (positive for additions, negative for usage) */
  amount: number;
  /** Description of the transaction */
  description: string;
  /** Optional JSON metadata */
  transaction_metadata?: string | null;
  /** Timestamp when transaction was created */
  created_at: string;
}

/**
 * Credit balance response
 */
export interface CreditBalanceResponse {
  /** User ID */
  user_id: number;
  /** Current credit balance */
  balance: number;
  /** Whether user has unlimited credits (admin) */
  is_unlimited: boolean;
}

/**
 * Stripe payment information
 */
export interface StripePaymentInfo {
  payment_intent_id?: string | null;
  session_id?: string | null;
  amount: number;
  currency: string;
  status: string;
  payment_method_type?: string | null;
  payment_method_brand?: string | null;
  payment_method_last4?: string | null;
  payment_date: string;
  amount_received?: number | null;
  application_fee_amount?: number | null;
  net_amount?: number | null;
  available_at?: string | null;
  refund_amount?: number | null;
  refund_date?: string | null;
  customer_country?: string | null;
  customer_email?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
}

/**
 * Credit purchase transaction with payment details
 */
export interface CreditPurchaseTransaction {
  transaction_id: number;
  user_id: number;
  user_name: string;
  user_email: string;
  credits_amount: number;
  credits_available_date: string;
  payment_info?: StripePaymentInfo | null;
  euros_amount?: number | null;
  description: string;
}

/**
 * Accounting summary
 */
export interface AccountingSummary {
  total_paid: number;
  total_refunded: number;
  total_stripe_fees: number;
  net_total: number;
  total_transactions: number;
  available_balance?: number | null;
}

/**
 * Accounting data response
 */
export interface AccountingResponse {
  summary: AccountingSummary;
  transactions: CreditPurchaseTransaction[];
}