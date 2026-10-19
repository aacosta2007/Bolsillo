import { api } from '@/shared/api/client';
import type { Category, CategoryInput, CategoryKind } from './types';

export const categoriesApi = {
  list: (kind?: CategoryKind) => api<Category[]>('/categories', { query: { kind } }),
  create: (body: CategoryInput) => api<Category>('/categories', { method: 'POST', body }),
  update: (id: string, body: Partial<CategoryInput>) => api<Category>(`/categories/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => api<void>(`/categories/${id}`, { method: 'DELETE' }),
};
