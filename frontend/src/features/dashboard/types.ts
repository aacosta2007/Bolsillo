import type { Account } from '../accounts/types';
import type { BudgetStatus } from '../budgets/types';
import type { UpcomingItem } from '../recurring/types';
import type { Transaction } from '../transactions/types';
import type { PayPeriod } from '../reports/types';

export interface CategoryTotal {
  category_id: string;
  name: string;
  color: string | null;
  icon: string | null;
  total: string;
  percent: number;
}

export interface TrendPoint {
  month: string;
  income: string;
  expense: string;
}

export interface NextPayday {
  date: string;
  amount: string;
  note: string | null;
}

export interface DashboardSummary {
  period: { from: string; to: string };
  total_balance: string;
  income: string;
  expense: string;
  net: string;
  savings_rate: number;
  by_category: CategoryTotal[];
  monthly_trend: TrendPoint[];
  accounts: Account[];
  budgets_at_risk: BudgetStatus[];
  upcoming_recurring: UpcomingItem[];
  recent_transactions: Transaction[];
  current_pay_period: PayPeriod | null;
  previous_pay_period: PayPeriod | null;
  next_payday: NextPayday | null;
}
