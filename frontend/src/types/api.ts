export type MeOut = { authenticated: true };

export type StatementOut = {
  id: number;
  period_start: string;
  period_end: string;
  filename: string | null;
  source: string;
  uploaded_at: string;
};

export type ParsedSummary = {
  statement_id: number;
  period_start: string;
  period_end: string;
  parsed_count: number;
  new_count: number;
  needs_review_count: number;
  warnings: string[];
};

export type TransactionOut = {
  id: number;
  statement_id: number;
  transaction_ref: string;
  utr_no: string | null;
  date: string;
  time: string | null;
  description: string;
  merchant_raw: string | null;
  merchant_normalized: string | null;
  amount: number | string;
  type: "debit" | "credit" | string;
  category_id: number | null;
  is_manually_categorized: boolean;
  needs_review: boolean;
  notes: string | null;
};

export type CategoryOut = {
  id: number;
  name: string;
  color: string;
  icon: string;
  is_system: boolean;
  excluded_from_spending: boolean;
  sort_order: number;
  mapping_count: number;
};

export type CategoryCreate = {
  name: string;
  color?: string;
  icon?: string;
  excluded_from_spending?: boolean;
  sort_order?: number;
};

export type CategoryPatch = {
  name?: string;
  color?: string;
  icon?: string;
  excluded_from_spending?: boolean;
  sort_order?: number;
};

export type MappingOut = {
  id: number;
  merchant_pattern: string;
  category_id: number;
  source: string;
  confidence: number | string | null;
  times_used: number;
  last_used_at: string | null;
};

export type MappingCreate = {
  merchant_pattern: string;
  category_id: number;
};

export type MappingPatch = {
  merchant_pattern?: string;
  category_id?: number;
};

export type PaginatedMappings = {
  items: MappingOut[];
  total: number;
};

export type BulkCategorizeItem = {
  transaction_id: number;
  category_id: number;
  remember: boolean;
};

export type BulkCategorize = {
  items: BulkCategorizeItem[];
};

export type PaginatedTransactions = {
  items: TransactionOut[];
  total: number;
};

export type ApiErrorBody = {
  error?: string;
  message?: string;
};

export type DashboardTotals = {
  income: string;
  expense: string;
  net: string;
  txn_count: number;
};

export type CategoryBreakdown = {
  category_id: number;
  name: string;
  color: string;
  total: string;
  txn_count: number;
  pct_of_expense: number;
};

export type TopMerchant = {
  merchant_normalized: string;
  total: string;
  txn_count: number;
  category_id: number;
};

export type DashboardOut = {
  month: number;
  year: number;
  totals: DashboardTotals;
  by_category: CategoryBreakdown[];
  top_merchants: TopMerchant[];
  recent_transactions: TransactionOut[];
  needs_review_count: number;
};

export type MoMMonth = {
  month: number;
  year: number;
  label: string;
  income: string;
  expense: string;
  net: string;
};

export type MoMOut = { months: MoMMonth[] };

export type TrendOut = {
  category: { id: number; name: string; color: string };
  months: Array<{ year: number; month: number; total: string; txn_count: number }>;
  top_merchants: Array<{ merchant_normalized: string; total: string }>;
};

export type InsightItem = {
  title: string;
  body: string;
  severity: "info" | "good" | "concern";
};

export type InsightsOut = {
  generated_at: string;
  model: string;
  insights: InsightItem[];
};

export type AnswerOut = {
  answer: string;
  context_used: {
    month: number;
    year: number;
    aggregations: string[];
  };
};
