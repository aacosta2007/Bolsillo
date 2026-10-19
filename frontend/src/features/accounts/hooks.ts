import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { accountsApi } from './api';
import type { AccountInput } from './types';

export const useAccounts = (includeArchived = false) =>
  useQuery({ queryKey: ['accounts', { includeArchived }], queryFn: () => accountsApi.list(includeArchived) });

function useInvalidateAccounts() {
  const qc = useQueryClient();
  // El saldo total y el resumen dependen de las cuentas.
  return () =>
    Promise.all([qc.invalidateQueries({ queryKey: ['accounts'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })]);
}

export function useCreateAccount() {
  const inv = useInvalidateAccounts();
  return useMutation({ mutationFn: (b: AccountInput) => accountsApi.create(b), onSuccess: inv });
}

export function useUpdateAccount() {
  const inv = useInvalidateAccounts();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<AccountInput> & { archived?: boolean }) =>
      accountsApi.update(id, body),
    onSuccess: inv,
  });
}

export function useDeleteAccount() {
  const inv = useInvalidateAccounts();
  return useMutation({ mutationFn: (id: string) => accountsApi.remove(id), onSuccess: inv });
}
