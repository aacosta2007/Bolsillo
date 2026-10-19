import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { invalidateMoney } from '@/shared/api/invalidate';
import { transactionsApi } from './api';
import type { TransactionFilters, TransactionInput } from './types';

export function useTransactionsInfinite(filters: TransactionFilters) {
  return useInfiniteQuery({
    queryKey: ['transactions', 'list', filters],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => transactionsApi.list(filters, pageParam, signal),
    getNextPageParam: (last) => (last.page * last.page_size < last.total ? last.page + 1 : undefined),
  });
}

export const useTransaction = (id: string | undefined) =>
  useQuery({ queryKey: ['transactions', 'detail', id], queryFn: () => transactionsApi.get(id!), enabled: !!id });

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: TransactionInput) => transactionsApi.create(b), onSuccess: () => invalidateMoney(qc) });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<TransactionInput>) => transactionsApi.update(id, body),
    onSuccess: () => invalidateMoney(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => transactionsApi.remove(id), onSuccess: () => invalidateMoney(qc) });
}
