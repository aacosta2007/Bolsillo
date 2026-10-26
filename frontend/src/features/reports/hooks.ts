import { useQuery } from '@tanstack/react-query';
import { reportsApi } from './api';

export const usePayPeriods = (count = 6) =>
  useQuery({ queryKey: ['reports', 'pay-periods', count], queryFn: () => reportsApi.payPeriods(count) });
