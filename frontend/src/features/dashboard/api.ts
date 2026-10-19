import { api } from '@/shared/api/client';
import type { DashboardSummary } from './types';

export const dashboardApi = {
  summary: (from?: string, to?: string) => api<DashboardSummary>('/dashboard/summary', { query: { from, to } }),
};
