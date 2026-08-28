// ── API ──────────────────────────────────────────────────────
export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data: T;
  timestamp: string;
  request_id: string;
}

// ── Portfolio ─────────────────────────────────────────────────
export type PortfolioMode = "BUILD" | "MANAGEMENT";

export interface Portfolio {
  id: number;
  name: string;
  currency: string;
  mode: PortfolioMode;
  target_capital: number;
  target_income: number;
}

export interface PortfolioSummary {
  total_invested: number;
  total_market_value: number;
  total_unrealized_profit: number;
  roi_pct: number;
  annual_income: number;
  monthly_income: number;
  cash_balance: number;
  goal_progress_pct: number;
  companies_count: number;
  total_shares: number;
}

// ── Company ───────────────────────────────────────────────────
export type CompanyStatus = "ACTIVE" | "WATCHLIST" | "ARCHIVED" | "DELISTED";
export type ShariaStatus  = "COMPLIANT" | "NON_COMPLIANT" | "UNDER_REVIEW" | "UNKNOWN";

export interface Company {
  id: number;
  symbol: string;
  company_name: string;
  exchange?: string;
  sector?: string;
  industry?: string;
  currency: string;
  status: CompanyStatus;
  sharia_status: ShariaStatus;
  finance_score: number;
  technical_score: number;
  logo_url?: string;
  color: string;
  notes?: string;
}

// ── Holding ───────────────────────────────────────────────────
export interface Holding {
  id: number;
  company_id: number;
  quantity: number;
  average_cost: number;
  invested_amount: number;
  market_value: number;
  last_price: number;
  unrealized_profit: number;
  unrealized_profit_pct: number;
  weight: number;
  installment_progress: number;
  total_dividends_received: number;
  total_bonus_shares: number;
  reinvestment_shares: number;
}

// ── Transaction ───────────────────────────────────────────────
export type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "BONUS" | "SPLIT" | "CORRECTION" | "REINVESTMENT";

export interface Transaction {
  id: number;
  company_id: number;
  transaction_type: TransactionType;
  quantity: number;
  price: number;
  fees: number;
  total_amount: number;
  notes?: string;
  executed_at: string;
}

// ── Installment ───────────────────────────────────────────────
export type InstallmentStatus = "WAITING" | "READY" | "EXECUTED" | "SKIPPED" | "CANCELLED";

export interface Installment {
  id: number;
  company_id: number;
  installment_number: number;
  target_price: number;
  allocated_amount: number;
  status: InstallmentStatus;
  executed_price?: number;
  executed_at?: string;
}

// ── Dividend ──────────────────────────────────────────────────
export interface Dividend {
  id: number;
  company_id: number;
  dividend_per_share: number;
  shares_at_time: number;
  received_amount: number;
  action: "CASH" | "REINVEST";
  ex_date?: string;
  payment_date?: string;
}

// ── Cash ──────────────────────────────────────────────────────
export interface Cash {
  available_cash: number;
  pending_cash: number;
  reinvestment_cash: number;
  total_cash: number;
}

// ── Goal ──────────────────────────────────────────────────────
export interface Goal {
  id: number;
  goal_name: string;
  target_value: number;
  current_value: number;
  completion_percentage: number;
  deadline?: string;
  status: "ACTIVE" | "ACHIEVED" | "PAUSED";
}

// ── Notification ──────────────────────────────────────────────
export type NotificationPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type NotificationStatus   = "UNREAD" | "READ" | "ARCHIVED";

export interface Notification {
  id: number;
  category: string;
  priority: NotificationPriority;
  title: string;
  message: string;
  status: NotificationStatus;
  created_at: string;
  read_at?: string;
}

// ── AI ────────────────────────────────────────────────────────
export interface AIResult {
  agent: string;
  success: boolean;
  summary: string;
  score?: number;
  confidence: number;
  evidence: any[];
  suggested_action: string;
}

export interface Evaluation {
  executive_summary: string;
  overall_confidence: number;
  conflicts: any[];
  opportunities: any[];
  risks: any[];
}

// ── Market ────────────────────────────────────────────────────
export interface MarketNews {
  id: number;
  headline: string;
  company?: string;
  category?: string;
  published: string;
}

export interface MarketEvent {
  id: number;
  type: string;
  symbol: string;
  date: string;
  description?: string;
}

// ── Share Return Indicator ────────────────────────────────────
export interface ShareReturnIndicator {
  reinvestment_shares: number;
  bonus_shares: number;
  total_free_shares: number;
  market_value: number;
  contribution_pct: number;
}
