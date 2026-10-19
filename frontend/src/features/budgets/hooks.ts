import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { budgetsApi } from './api';
import type { BudgetInput } from './types';

export const useBudgets = (month: string) =>
  useQuery({ queryKey: ['budgets', month], queryFn: () => budgetsApi.list(month) });

function useInvalidateBudgets() {
  const qc = useQueryClient();
  return () => Promise.all([qc.invalidateQueries({ queryKey: ['budgets'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })]);
}

export function useCreateBudget() {
  const inv = useInvalidateBudgets();
  return useMutation({ mutationFn: (b: BudgetInput) => budgetsApi.create(b), onSuccess: inv });
}

export function useUpdateBudget() {
  const inv = useInvalidateBudgets();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; amount_limit?: string; alert_threshold?: number }) => budgetsApi.update(id, body),
    onSuccess: inv,
  });
}

export function useDeleteBudget() {
  const inv = useInvalidateBudgets();
  return useMutation({ mutationFn: (id: string) => budgetsApi.remove(id), onSuccess: inv });
}

export function useCopyBudgets() {
  const inv = useInvalidateBudgets();
  return useMutation({
    mutationFn: ({ from, to }: { from: string; to: string }) => budgetsApi.copy(from, to),
    onSuccess: inv,
  });
}
