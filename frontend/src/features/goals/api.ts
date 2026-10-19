import { api } from '@/shared/api/client';
import type { Contribution, ContributionInput, Goal, GoalInput } from './types';

export const goalsApi = {
  list: () => api<Goal[]>('/goals'),
  create: (body: GoalInput) => api<Goal>('/goals', { method: 'POST', body }),
  update: (id: string, body: Partial<GoalInput>) => api<Goal>(`/goals/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => api<void>(`/goals/${id}`, { method: 'DELETE' }),
  contributions: (id: string) => api<Contribution[]>(`/goals/${id}/contributions`),
  addContribution: (id: string, body: ContributionInput) =>
    api<Contribution>(`/goals/${id}/contributions`, { method: 'POST', body }),
  removeContribution: (id: string, cid: string) => api<void>(`/goals/${id}/contributions/${cid}`, { method: 'DELETE' }),
};
