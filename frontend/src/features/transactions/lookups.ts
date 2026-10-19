import { useMemo } from 'react';
import { useAccounts } from '../accounts/hooks';
import type { Account } from '../accounts/types';
import { useCategories } from '../categories/hooks';
import type { Category } from '../categories/types';

/** Catálogos (cuentas incl. archivadas y categorías) indexados por id. */
export function useLookups() {
  const cats = useCategories();
  const accs = useAccounts(true);
  const categoryMap = useMemo(() => new Map<string, Category>((cats.data ?? []).map((c) => [c.id, c])), [cats.data]);
  const accountMap = useMemo(() => new Map<string, Account>((accs.data ?? []).map((a) => [a.id, a])), [accs.data]);
  return { categoryMap, accountMap, categories: cats.data ?? [], accounts: accs.data ?? [], ready: !cats.isLoading && !accs.isLoading };
}

export type Lookups = ReturnType<typeof useLookups>;
