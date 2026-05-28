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
