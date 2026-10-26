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
