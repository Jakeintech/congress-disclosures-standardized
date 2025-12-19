/**
 * API Types - Strict TypeScript interfaces for all API responses
 *
 * Based on actual API responses from:
 * - https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com
 * - Congress.gov API (https://api.congress.gov)
 */

// ============================================================================
// Common Types
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

export interface PaginationMeta {
  total: number;
  count: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardSummary {
  members: {
    total: number;
  };
  trades: {
    total: number;
    unique_stocks: number;
    latest_transaction: string; // ISO date
  };
  filings: {
    total: number;
    latest_filing: string; // YYYYMMDD format
    earliest_filing: string;
    coverage_years: number[];
  };
  bills: {
    total: number;
  };
  last_updated: string; // YYYYMMDD format
}

export interface TrendingStock {
  ticker: string;
  company_name?: string;
  trade_count: number;
  net_direction?: 'buy' | 'sale' | 'exchange';
  buy_count?: number;
  sale_count?: number;
  total_volume?: number;
  avg_amount?: number;
}

export interface TopTrader {
  name: string;
  bioguide_id: string;
  party?: 'D' | 'R' | 'I';
  state?: string;
  chamber?: 'house' | 'senate';
  trade_count: number;
  total_volume?: string;
  avg_amount?: number;
  latest_trade_date?: string;
}

// ============================================================================
// Member Types
// ============================================================================

export interface CongressMember {
  bioguide_id: string;
  first_name: string;
  last_name: string;
  direct_order_name: string;
  party: 'D' | 'R' | 'I' | string;
  state: string;
  district?: number | null;
  chamber: 'house' | 'senate';
  birth_year?: string;
  image_url?: string;
  official_url?: string;
  is_current: boolean;
  sponsored_legislation_count?: number;
  cosponsored_legislation_count?: number;
  terms_data?: string; // JSON string of term objects
  bills_sponsored_count?: number;
  gold_created_at?: string;
  gold_version?: number;
  total_trades?: number;
  total_volume?: number;
  unique_stocks?: number;
  last_trade_date?: string;
}

export interface MemberProfile extends CongressMember {
  full_name?: string;
  honorific_prefix?: string;
  middle_name?: string;
  nickname?: string;
  suffix?: string;
  contact_info?: {
    phone?: string;
    email?: string;
    office?: string;
  };
  social_media?: {
    twitter?: string;
    facebook?: string;
    youtube?: string;
  };
  committees?: Committee[];
  leadership_roles?: LeadershipRole[];
}

export interface MembersParams extends PaginationParams {
  congress?: number;
  chamber?: 'house' | 'senate';
  party?: 'D' | 'R' | 'I';
  state?: string;
  is_current?: boolean;
  sortBy?: 'total_trades' | 'total_volume' | 'name' | 'last_name';
  sortOrder?: 'asc' | 'desc';
}

export interface Committee {
  system_code: string;
  name: string;
  chamber: 'house' | 'senate' | 'joint';
  type: string;
  subcommittees?: Subcommittee[];
}

export interface Subcommittee {
  system_code: string;
  name: string;
  parent_committee: string;
}

export interface LeadershipRole {
  title: string;
  congress: number;
  start_year: number;
  end_year?: number;
}

// ============================================================================
// Bill Types
// ============================================================================

export interface Bill {
  bill_id: string;
  congress: number;
  bill_type: 'hr' | 's' | 'hjres' | 'sjres' | 'hconres' | 'sconres' | 'hres' | 'sres';
  bill_number: number;
  title: string;
  origin_chamber?: 'house' | 'senate';
  introduced_date?: string;
  latest_action_date?: string;
  latest_action_text?: string;
  sponsor_bioguide_id?: string;
  sponsor_name?: string;
  sponsor_party?: string;
  sponsor_state?: string;
  cosponsors_count?: number;
  committees?: string[];
  subjects?: string[];
  policy_area?: string;
  summary?: string;
  update_date?: string;
  congress_gov_url?: string;
}

export interface BillDetail {
  bill: Bill;
  sponsor?: Sponsor;
  cosponsors?: Cosponsor[];
  cosponsors_count: number;
  actions_recent?: BillAction[];
  actions?: BillAction[];
  actions_count_total: number;
  industry_tags?: string[];
  trade_correlations?: TradeCorrelation[];
  trade_correlations_count: number;
  summary?: BillSummary;
  text_versions?: TextVersion[];
  subjects?: Subject[];
  titles?: BillTitle[];
  congress_gov_url?: string;
}

export interface Sponsor {
  bioguide_id: string;
  name: string;
  party: string;
  state: string;
  district?: number;
  chamber?: 'house' | 'senate';
  image_url?: string;
}

export interface Cosponsor {
  bioguideId: string;
  name: string;
  state: string;
  party: string;
  district?: string;
  sponsorshipDate: string;
  isOriginalCosponsor: boolean;
}

export interface BillAction {
  action_date: string;
  action_text: string;
  type?: string;
  action_code?: string;
  source_system?: string;
  committees?: string[];
}

export interface BillSummary {
  updateDate: string;
  actionDate: string;
  actionDesc: string;
  text: string;
  versionCode: string;
}

export interface TextVersion {
  type: string;
  date: string;
  formats: TextFormat[];
}

export interface TextFormat {
  type: 'pdf' | 'html' | 'xml' | 'txt';
  url: string;
}

export interface Subject {
  name: string;
  updateDate?: string;
}

export interface BillTitle {
  type: string;
  title: string;
  chamber?: string;
  congress?: number;
}

export interface TradeCorrelation {
  bill_id: string;
  member_name: string;
  bioguide_id: string;
  ticker: string;
  trade_date: string;
  transaction_type: 'purchase' | 'sale' | 'exchange';
  amount_range: string;
  correlation_score: number;
}

export interface BillsParams extends PaginationParams {
  congress?: number;
  billType?: string;
  sponsor?: string;
  industry?: string;
  hasTradeCorrelations?: boolean;
  sortBy?: 'latest_action_date' | 'cosponsors_count' | 'trade_correlation_score' | 'introduced_date';
  sortOrder?: 'asc' | 'desc';
}

// ============================================================================
// Transaction Types
// ============================================================================

export interface Transaction {
  doc_id: string;
  filing_year: number;
  filing_date: string | null;
  filing_date_key: number | null;
  filer_name: string | null;
  first_name: string | null;
  last_name: string | null;
  state_district: string | null;
  bioguide_id: string | null;
  party: 'D' | 'R' | 'I' | null;
  state: string | null;
  chamber: 'house' | 'senate' | null;
  transaction_date: string;
  transaction_date_key: number;
  owner: string | null;
  ticker: string;
  asset_description: string;
  asset_type: 'Stock' | 'Bond' | 'Mutual Fund' | 'ETF' | 'Cryptocurrency' | string;
  transaction_type: 'Purchase' | 'Sale' | 'Exchange' | string;
  amount: string;
  amount_low: number;
  amount_high: number;
  comment: string | null;
  cap_gains_over_200: boolean;
  transaction_key: string;
  year: number;
}

export interface TransactionsParams extends PaginationParams {
  ticker?: string;
  member?: string;
  tradeType?: 'purchase' | 'sale' | 'exchange';
  minAmount?: string;
  startDate?: string;
  endDate?: string;
}

// ============================================================================
// Lobbying Types
// ============================================================================

export interface TripleCorrelation {
  bill_id: string;
  client_names: string;
  client_count: number;
  registrant_names: string;
  registrant_count: number;
  lobbying_amount: number;
  filing_count: number;
  top_issue_codes: string;
  raw_reference: string;
  first_filing_date: string;
  last_filing_date: string;
  correlation_score: number;
  year: number;
  dt_computed: string;
  __index_level_0__?: number;
}

export interface TripleCorrelationsParams extends PaginationParams {
  minScore?: number;
  year?: number;
}

export interface NetworkGraphNode {
  id: string;
  name?: string;
  group: 'member' | 'asset' | 'person' | 'bill' | 'party_agg';
  type?: 'member' | 'asset' | 'person' | 'bill' | 'party_agg' | 'client' | 'lobbyist'; // Legacy/Lobbying alias
  subgroup?: 'family';
  party?: string;
  state?: string;
  chamber?: string;
  value?: number;
  spend?: number; // For lobbying
  connections?: number; // For lobbying
  transaction_count?: number;
  degree?: number;
  is_primary?: boolean;
  owner_code?: string;
  title?: string; // For bills
  // D3 simulation properties
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface NetworkGraphLink {
  source: string | NetworkGraphNode;
  target: string | NetworkGraphNode;
  value?: number;
  count?: number;
  type?: 'trade' | 'relationship' | 'sponsorship' | 'mixed' | 'purchase' | 'sale';
  is_aggregated?: boolean;
}

export interface NetworkGraphData {
  graph?: {
    nodes: NetworkGraphNode[];
    links: NetworkGraphLink[];
  };
  nodes?: NetworkGraphNode[];
  links?: NetworkGraphLink[];
  aggregated_nodes?: NetworkGraphNode[];
  aggregated_links?: NetworkGraphLink[];
  metadata?: {
    year: string;
    node_count: number;
    link_count: number;
  };
  summary_stats?: {
    total_members: number;
    total_assets: number;
    total_links: number;
    total_transactions: number;
  };
}

// ============================================================================
// Amendment Types
// ============================================================================

export interface Amendment {
  congress: number;
  type: string;
  number: number;
  description: string;
  purpose: string;
  updateDate: string;
  latestAction?: {
    actionDate: string;
    text: string;
  };
  sponsor?: Sponsor;
  amendedBill?: {
    congress: number;
    type: string;
    number: number;
  };
}

// ============================================================================
// Related Bills Types
// ============================================================================

export interface RelatedBill {
  congress: number;
  type: string;
  number: number;
  title: string;
  relationshipType: string;
  latestAction?: {
    actionDate: string;
    text: string;
  };
}

// ============================================================================
// Portfolio Types
// ============================================================================

export interface PortfolioHolding {
  ticker?: string;
  asset_description: string;
  asset_type: string;
  value_range: string;
  value_low?: number;
  value_high?: number;
  income_range?: string;
  filing_date: string;
  doc_id: string;
}

export interface MemberPortfolio {
  bioguide_id: string;
  member_name: string;
  holdings: PortfolioHolding[];
  total_value_range: string;
  last_updated: string;
}

// ============================================================================
// Stock Activity Types
// ============================================================================

export interface StockActivity {
  ticker: string;
  company_name?: string;
  trade_count: number;
  member_count: number;
  total_volume: number;
  buy_count: number;
  sale_count: number;
  latest_trade_date: string;
  top_traders: Array<{
    bioguide_id: string;
    name: string;
    trade_count: number;
  }>;
}

// ============================================================================
// Compliance Types
// ============================================================================

export interface ComplianceMetrics {
  total_members: number;
  total_filings: number;
  on_time_filings: number;
  late_filings: number;
  compliance_rate: number;
  avg_days_late: number;
  members_with_violations: number;
}

// ============================================================================
// Type Guards
// ============================================================================

export function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'success' in value &&
    typeof (value as any).success === 'boolean'
  );
}

export function isCongressMember(value: unknown): value is CongressMember {
  return (
    typeof value === 'object' &&
    value !== null &&
    'bioguide_id' in value &&
    typeof (value as any).bioguide_id === 'string'
  );
}

export function isBill(value: unknown): value is Bill {
  return (
    typeof value === 'object' &&
    value !== null &&
    'bill_id' in value &&
    typeof (value as any).bill_id === 'string'
  );
}
