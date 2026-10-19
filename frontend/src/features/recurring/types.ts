export type Frequency = 'daily' | 'weekly' | 'monthly' | 'yearly';

export interface RecurringRule {
  id: string;
  type: 'income' | 'expense';
  amount: string;
  account_id: string;
  category_id: string;
  note: string | null;
  frequency: Frequency;
  interval: number;
  start_date: string;
  end_date: string | null;
  next_run_date: string;
  active: boolean;
}

export interface RecurringInput {
  type: 'income' | 'expense';
  amount: string;
  account_id: string;
  category_id: string;
  note?: string | null;
  frequency: Frequency;
  interval: number;
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
}
