import { api, apiBlob } from '@/shared/api/client';
import type { Page, Transaction, TransactionFilters, TransactionInput } from './types';

export const PAGE_SIZE = 50;

export const transactionsApi = {
  list: (filters: TransactionFilters, page: number, signal?: AbortSignal) =>
    api<Page<Transaction>>('/transactions', { query: { ...filters, page, page_size: PAGE_SIZE }, signal }),
  get: (id: string) => api<Transaction>(`/transactions/${id}`),
  create: (body: TransactionInput) => api<Transaction>('/transactions', { method: 'POST', body }),
  update: (id: string, body: Partial<TransactionInput>) => api<Transaction>(`/transactions/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => api<void>(`/transactions/${id}`, { method: 'DELETE' }),
  exportCsv: (from: string, to: string) => apiBlob('/export/csv', { query: { from, to } }),
};
