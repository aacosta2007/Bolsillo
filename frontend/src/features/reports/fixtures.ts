import type { MonthlyReport, PayPeriod } from './types';

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
    salary_income: '1350000.00',
    extra_income: '0.00',
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

export function makeMonthlyReport(over: Partial<MonthlyReport> = {}): MonthlyReport {
  return {
    month: '2026-10',
    is_partial: false,
    generated_at: '2026-11-01T13:00:00Z',
    currency: 'COP',
    summary: {
      income: '2350000.00',
      expense: '1684300.00',
      net: '665700.00',
      savings_rate: 28.3,
      prev: { income: '2000000.00', expense: '1590000.00', net: '410000.00', savings_rate: 20.5 },
      income_change_pct: 17.5,
      expense_change_pct: 5.9,
      net_change_pct: 62.4,
    },
    expense_by_category: [
      { category_id: 'c1', name: 'Comida', color: '#0F5E55', icon: 'utensils', total: '452300.00', prev_total: '383300.00', change_pct: 18.0, percent: 26.9, count: 14 },
      { category_id: 'c2', name: 'Transporte', color: '#E58A2E', icon: 'bus', total: '120000.00', prev_total: '150000.00', change_pct: -20.0, percent: 7.1, count: 8 },
      { category_id: 'c3', name: 'Ocio', color: '#7C3AED', icon: 'film', total: '0.00', prev_total: '80000.00', change_pct: -100, percent: 0, count: 0 },
      { category_id: 'c4', name: 'Salud', color: '#B33A0A', icon: 'heart', total: '50000.00', prev_total: '50000.00', change_pct: 0.0, percent: 3, count: 1 },
    ],
    income_by_category: [
      { category_id: 'i1', name: 'Salario', color: '#1D4ED8', icon: 'briefcase', total: '2000000.00', prev_total: '2000000.00', change_pct: 0.0, percent: 85.1, count: 2, is_new: false },
      { category_id: 'i2', name: 'Freelance', color: '#0F5E55', icon: 'laptop', total: '350000.00', prev_total: '0.00', change_pct: null, percent: 14.9, count: 1, is_new: true },
    ],
    top_expenses: [{ transaction_id: 't1', date: '2026-10-05', note: 'Arriendo', category: 'Hogar/Arriendo', account: 'Bancolombia', amount: '700000.00' }],
    daily: [
      { date: '2026-10-01', expense: '12000.00', income: '0.00', is_payday: false },
      { date: '2026-10-02', expense: '0.00', income: '1000000.00', is_payday: true },
      { date: '2026-10-05', expense: '715000.00', income: '0.00', is_payday: false },
    ],
    daily_stats: { max_day: '2026-10-05', max_day_expense: '715000.00', avg_daily_expense: '54332.26', no_spend_days: 4 },
    pay_periods: [
      makePeriod({ start: '2026-09-30', end: '2026-10-14', in_progress: false, days_elapsed: 15, days_remaining: 0, net: '97900.00', spent_per_day: '60140.00', status: 'justo' }),
      makePeriod(),
    ],
    budgets: [
      { id: 'b2', category_id: 'c2', month: '2026-10', amount_limit: '300000.00', alert_threshold: '80', spent: '120000.00', remaining: '180000.00', percent: 40, status: 'ok' },
      { id: 'b1', category_id: 'c1', month: '2026-10', amount_limit: '400000.00', alert_threshold: '80', spent: '452300.00', remaining: '-52300.00', percent: 113, status: 'exceeded' },
    ],
    budgets_summary: { ok: 3, warning: 1, exceeded: 1 },
    goals: [
      { id: 'g1', name: 'Viaje a Cartagena', color: '#0F5E55', target_amount: '3000000.00', saved: '1050000.00', percent: 35, contributed_this_month: '300000.00', monthly_needed: '275000.00', status: 'on_track' },
      { id: 'g2', name: 'Fondo de emergencia', color: '#1D4ED8', target_amount: '5000000.00', saved: '0.00', percent: 0, contributed_this_month: '0.00', monthly_needed: '400000.00', status: 'behind' },
    ],
    trend: [],
    insights: [
      { kind: 'category_up', tone: 'warning', text: 'Gastaste 18 % más en Comida que en septiembre ($ 69.000 más).' },
      { kind: 'savings_record', tone: 'positive', text: 'Tu mejor ahorro en 6 meses.' },
    ],
    ...over,
  };
}
