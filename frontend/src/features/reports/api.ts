import { api } from '@/shared/api/client';
import type { PayPeriod } from './types';

export const reportsApi = {
  payPeriods: (count = 6) => api<PayPeriod[]>('/reports/pay-periods', { query: { count } }),
};
