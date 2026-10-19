import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { categoriesApi } from './api';
import type { Category, CategoryInput, CategoryKind } from './types';

export const useCategories = (kind?: CategoryKind) =>
  useQuery({ queryKey: ['categories', { kind: kind ?? 'all' }], queryFn: () => categoriesApi.list(kind) });

/** Mapa id → categoría para resolver nombres/iconos en listas. */
export function useCategoryMap() {
  const q = useCategories();
  const map = useMemo(() => new Map<string, Category>((q.data ?? []).map((c) => [c.id, c])), [q.data]);
  return { map, ...q };
}

function useInvalidateCategories() {
  const qc = useQueryClient();
  return () =>
    Promise.all(
      ['categories', 'transactions', 'budgets', 'dashboard'].map((k) => qc.invalidateQueries({ queryKey: [k] })),
    );
}

export function useCreateCategory() {
  const inv = useInvalidateCategories();
  return useMutation({ mutationFn: (b: CategoryInput) => categoriesApi.create(b), onSuccess: inv });
}

export function useUpdateCategory() {
  const inv = useInvalidateCategories();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<CategoryInput>) => categoriesApi.update(id, body),
    onSuccess: inv,
  });
}

export function useDeleteCategory() {
  const inv = useInvalidateCategories();
  return useMutation({ mutationFn: (id: string) => categoriesApi.remove(id), onSuccess: inv });
}
