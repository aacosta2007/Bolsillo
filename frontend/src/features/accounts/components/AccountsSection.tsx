import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Card, CardHeader, EmptyState, ErrorState, IconBadge, ListSkeleton, Money, cn } from '@/shared/ui';
import { useAccounts } from '../hooks';
import type { Account } from '../types';
import { ACCOUNT_TYPES } from '../types';
import { AccountFormSheet } from './AccountFormSheet';

export function AccountsSection() {
  const q = useAccounts(true);
  const [editing, setEditing] = useState<Account | null>(null);
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <CardHeader
        title="Cuentas"
        aside={
          <button
            type="button"
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
            className="flex min-h-[44px] items-center gap-1 font-semibold text-primary"
          >
            <Plus size={16} aria-hidden="true" />
            Nueva
          </button>
        }
      />
      {q.isLoading && <ListSkeleton rows={3} />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.isSuccess && q.data.length === 0 && <EmptyState title="Sin cuentas" message="Crea tu primera cuenta para registrar movimientos." />}
      <ul className="divide-y divide-line-soft">
        {q.data?.map((a) => (
          <li key={a.id}>
            <button
              type="button"
              onClick={() => {
                setEditing(a);
                setOpen(true);
              }}
              aria-label={`Editar cuenta ${a.name}`}
              className={cn('flex min-h-[56px] w-full items-center gap-3 py-2 text-left', a.archived && 'opacity-60')}
            >
              <IconBadge icon={a.icon} color={a.color} />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-sm font-semibold">{a.name}</span>
                <span className="text-xs text-muted">
                  {ACCOUNT_TYPES.find((t) => t.value === a.type)?.label}
                  {a.archived && ' · Archivada'}
                </span>
              </span>
              <Money value={a.balance} className="text-sm font-bold" />
            </button>
          </li>
        ))}
      </ul>
      <AccountFormSheet open={open} onOpenChange={setOpen} account={editing} />
    </Card>
  );
}
