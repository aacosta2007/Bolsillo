import type { PayPeriod } from './types';

export function makePeriod(over: Partial<PayPeriod> = {}): PayPeriod {
  return {
    start: '2026-10-15',
    end: '2026-10-29',
    days: 15,
    days_elapsed: 6,
    days_remaining: 10,
    in_progress: true,
    source: 'paycheck',
    income: '1350000.00',
    expense: '612400.00',
    net: '737600.00',
    spent_per_day: '102066.67',
    available_per_day: '73760.00',
    spent_percent: 45.4,
    time_percent: 40.0,
    status: 'en_curso',
    by_category: [],
    ...over,
  };
}
