export type Frequency = 'daily' | 'weekly' | 'monthly' | 'yearly' | 'monthly_days';
export type WeekendAdjust = 'none' | 'previous_business_day';

export interface RecurringRule {
  id: string;
  type: 'income' | 'expense';
  amount: string;
  account_id: string;
  category_id: string;
  note: string | null;
  frequency: Frequency;
  interval: number;
  /** Solo con `monthly_days`: "15,L", "15,30", "5"… (1 a 3 valores; L = último día). */
  days_of_month: string | null;
  weekend_adjust: WeekendAdjust;
  is_paycheck: boolean;
  start_date: string;
  end_date: string | null;
  next_run_date: string;
  active: boolean;
  /** Equivalente mensual aproximado, calculado por el API ("2000000.00"). */
  monthly_equivalent: string;
}

export interface RecurringInput {
  type: 'income' | 'expense';
  amount: string;
  account_id: string;
  category_id: string;
  note?: string | null;
  frequency: Frequency;
  interval: number;
  days_of_month: string | null;
  weekend_adjust: WeekendAdjust;
  is_paycheck: boolean;
  start_date: string;
  end_date?: string | null;
  active?: boolean;
}

export interface UpcomingItem {
  rule_id: string;
  date: string;
  type: 'income' | 'expense';
  amount: string;
  category_id: string;
  account_id: string;
  note: string | null;
  is_paycheck: boolean;
}
