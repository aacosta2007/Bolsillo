import { api } from '@/shared/api/client';
import type { RecurringInput, RecurringRule, UpcomingItem } from './types';

export const recurringApi = {
  list: () => api<RecurringRule[]>('/recurring'),
  create: (body: RecurringInput) => api<RecurringRule>('/recurring', { method: 'POST', body }),
  update: (id: string, body: Partial<RecurringInput>) => api<RecurringRule>(`/recurring/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => api<void>(`/recurring/${id}`, { method: 'DELETE' }),
  run: () => api<{ created: number }>('/recurring/run', { method: 'POST' }),
  upcoming: (days = 30) => api<UpcomingItem[]>('/recurring/upcoming', { query: { days } }),
};
