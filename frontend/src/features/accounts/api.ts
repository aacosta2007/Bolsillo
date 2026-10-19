import { api } from '@/shared/api/client';
import type { Account, AccountInput } from './types';

export const accountsApi = {
  list: (includeArchived = false) => api<Account[]>('/accounts', { query: { include_archived: includeArchived } }),
  create: (body: AccountInput) => api<Account>('/accounts', { method: 'POST', body }),
  update: (id: string, body: Partial<AccountInput> & { archived?: boolean }) =>
    api<Account>(`/accounts/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => api<void>(`/accounts/${id}`, { method: 'DELETE' }),
};
