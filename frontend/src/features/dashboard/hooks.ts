import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from './api';

export const useDashboardSummary = (from?: string, to?: string) =>
  useQuery({ queryKey: ['dashboard', 'summary', from, to], queryFn: () => dashboardApi.summary(from, to) });
