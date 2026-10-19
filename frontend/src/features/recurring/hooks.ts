import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { invalidateMoney } from '@/shared/api/invalidate';
import { recurringApi } from './api';
import type { RecurringInput } from './types';

export const useRecurring = () => useQuery({ queryKey: ['recurring', 'rules'], queryFn: recurringApi.list });

export const useUpcoming = (days = 30) =>
  useQuery({ queryKey: ['recurring', 'upcoming', days], queryFn: () => recurringApi.upcoming(days) });

function useInvalidateRecurring() {
  const qc = useQueryClient();
  return () => Promise.all([qc.invalidateQueries({ queryKey: ['recurring'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })]);
}

export function useCreateRecurring() {
  const inv = useInvalidateRecurring();
  return useMutation({ mutationFn: (b: RecurringInput) => recurringApi.create(b), onSuccess: inv });
}

export function useUpdateRecurring() {
  const inv = useInvalidateRecurring();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<RecurringInput>) => recurringApi.update(id, body),
    onSuccess: inv,
  });
}

export function useDeleteRecurring() {
  const inv = useInvalidateRecurring();
  return useMutation({ mutationFn: (id: string) => recurringApi.remove(id), onSuccess: inv });
}

/** Ejecutar pendientes crea movimientos: afecta saldos, presupuestos y listas. */
export function useRunRecurring() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => recurringApi.run(), onSuccess: () => invalidateMoney(qc) });
}
