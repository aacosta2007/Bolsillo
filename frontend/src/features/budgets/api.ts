import { api } from '@/shared/api/client';
import type { BudgetInput, BudgetStatus } from './types';

export const budgetsApi = {
  list: (month: string) => api<BudgetStatus[]>('/budgets', { query: { month } }),
  create: (body: BudgetInput) => api<BudgetStatus>('/budgets', { method: 'POST', body }),
  update: (id: string, body: Partial<Pick<BudgetInput, 'amount_limit' | 'alert_threshold'>>) =>
    api<BudgetStatus>(`/budgets/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => api<void>(`/budgets/${id}`, { method: 'DELETE' }),
  copy: (from_month: string, to_month: string) =>
    api<BudgetStatus[]>('/budgets/copy', { method: 'POST', body: { from_month, to_month } }),
};
