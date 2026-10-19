import type { QueryClient } from '@tanstack/react-query';

/** Todo lo que depende de movimientos/saldos. */
export function invalidateMoney(qc: QueryClient) {
  return Promise.all(
    ['transactions', 'dashboard', 'accounts', 'budgets', 'recurring', 'goals'].map((k) =>
      qc.invalidateQueries({ queryKey: [k] }),
    ),
  );
}
