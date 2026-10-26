import { api, apiBlob } from '@/shared/api/client';
import type { MonthlyReport, PayPeriod } from './types';

export const reportsApi = {
  payPeriods: (count = 6) => api<PayPeriod[]>('/reports/pay-periods', { query: { count } }),
  monthly: (month: string) => api<MonthlyReport>(`/reports/monthly/${month}`),
  /** PDF autenticado (fetch con token, no un enlace directo). */
  monthlyPdf: (month: string) => apiBlob(`/reports/monthly/${month}.pdf`),
};
