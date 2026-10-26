import type { BudgetStatus } from '../budgets/types';
import type { CategoryTotal } from '../dashboard/types';

export type PayPeriodStatus = 'en_curso' | 'ahorro' | 'justo' | 'deficit';

export interface PayPeriod {
  start: string;
  end: string;
  days: number;
  days_elapsed: number;
  days_remaining: number;
  in_progress: boolean;
  source: 'paycheck' | 'calendar';
  income: string;
  expense: string;
  net: string;
  spent_per_day: string | null;
  available_per_day: string | null;
  spent_percent: number;
  time_percent: number;
  status: PayPeriodStatus;
  by_category: CategoryTotal[];
}

export type InsightTone = 'positive' | 'warning' | 'neutral';

export interface MonthlySummary {
  income: string;
  expense: string;
  net: string;
  savings_rate: number | null;
  prev: { income: string; expense: string; net: string; savings_rate: number | null } | null;
  income_change_pct: number | null;
  expense_change_pct: number | null;
  net_change_pct: number | null;
}

export interface MonthlyCategory {
  category_id: string;
  name: string;
  color: string | null;
  icon: string | null;
  total: string;
  prev_total: string;
  change_pct: number | null;
  percent: number;
  count: number;
  is_new?: boolean;
}

export interface MonthlyTopExpense {
  transaction_id: string;
  date: string;
  note: string | null;
  category: string;
  account: string;
  amount: string;
}

export interface MonthlyDay {
  date: string;
  expense: string;
  income: string;
  is_payday: boolean;
}

export interface MonthlyDailyStats {
  max_day: string | null;
  max_day_expense: string;
  avg_daily_expense: string;
  no_spend_days: number;
}

export type MonthlyGoalStatus = 'on_track' | 'behind' | 'completed' | 'no_target_date';

export interface MonthlyGoal {
  id: string;
  name: string;
  color: string | null;
  target_amount: string;
  saved: string;
  percent: number;
  contributed_this_month: string;
  monthly_needed: string | null;
  status: MonthlyGoalStatus;
}

export interface MonthlyInsight {
  kind: string;
  tone: InsightTone;
  text: string;
}

export interface MonthlyReport {
  month: string;
  is_partial: boolean;
  generated_at: string;
  currency: string;
  summary: MonthlySummary;
  expense_by_category: MonthlyCategory[];
  income_by_category: MonthlyCategory[];
  top_expenses: MonthlyTopExpense[];
  daily: MonthlyDay[];
  daily_stats: MonthlyDailyStats;
  pay_periods: PayPeriod[];
  budgets: BudgetStatus[];
  budgets_summary: { ok: number; warning: number; exceeded: number };
  goals: MonthlyGoal[];
  trend: Array<{ month: string; income: string; expense: string; net: string; savings_rate: number | null }>;
  insights: MonthlyInsight[];
}
