import { useMemo, useState } from 'react';
import { Play, Repeat } from 'lucide-react';
import { FREQ_LABEL, shortDate } from '@/shared/lib/dates';
import { formatMoney, fromCents, toCents } from '@/shared/lib/money';
import { Button, EmptyState, ErrorState, ListSkeleton, Money, cn, errorMessage } from '@/shared/ui';
import { useAccounts } from '../../accounts/hooks';
import { useCategories } from '../../categories/hooks';
import { useRecurring, useRunRecurring, useUpcoming } from '../hooks';
import type { RecurringRule } from '../types';
import { RecurringFormSheet } from './RecurringFormSheet';

/** Equivalente mensual aproximado (centavos) de una regla de gasto. */
export function monthlyCents(r: Pick<RecurringRule, 'amount' | 'frequency' | 'interval'>): bigint {
  const c = toCents(r.amount);
  const n = BigInt(Math.max(1, r.interval));
  switch (r.frequency) {
    case 'daily':
      return (c * 365n) / (12n * n);
    case 'weekly':
      return (c * 52n) / (12n * n);
    case 'monthly':
      return c / n;
    case 'yearly':
      return c / (12n * n);
  }
}

function ruleMeta(r: RecurringRule, accName?: string): string {
  const unit = { daily: 'día', weekly: 'semana', monthly: 'mes', yearly: 'año' }[r.frequency];
  const base =
    r.interval > 1
      ? `Cada ${r.interval} ${r.frequency === 'monthly' ? 'meses' : r.frequency === 'daily' ? 'días' : r.frequency === 'weekly' ? 'semanas' : 'años'}`
      : (FREQ_LABEL[r.frequency] ?? unit);
  const day = r.frequency === 'monthly' || r.frequency === 'yearly' ? `día ${Number(r.start_date.slice(8, 10))}` : null;
  return [base, day, accName, !r.active ? 'Pausado' : null].filter(Boolean).join(' · ');
}

export function RecurringTab() {
  const rules = useRecurring();
  const upcoming = useUpcoming(30);
  const accounts = useAccounts(true);
  const categories = useCategories();
  const run = useRunRecurring();
  const [editing, setEditing] = useState<RecurringRule | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const accMap = useMemo(() => new Map((accounts.data ?? []).map((a) => [a.id, a.name])), [accounts.data]);
  const catMap = useMemo(() => new Map((categories.data ?? []).map((c) => [c.id, c.name])), [categories.data]);

  const fixed = useMemo(
    () => fromCents((rules.data ?? []).filter((r) => r.active && r.type === 'expense').reduce((acc, r) => acc + monthlyCents(r), 0n)),
    [rules.data],
  );
  const next = upcoming.data?.[0];

  return (
    <div className="flex flex-col gap-3">
      {rules.isLoading && <ListSkeleton rows={4} />}
      {rules.isError && <ErrorState error={rules.error} onRetry={() => rules.refetch()} />}

      {rules.isSuccess && rules.data.length > 0 && (
        <div className="flex items-center justify-between rounded-[18px] bg-surface px-4 py-3.5">
          <div className="flex flex-col">
            <span className="text-xs text-muted">Fijos al mes</span>
            <span className="tnum text-lg font-bold">{formatMoney(fixed)}</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-xs text-muted">Próximo cobro</span>
            <span className="text-sm font-semibold">{next ? `${next.note || catMap.get(next.category_id) || 'Recurrente'} · ${shortDate(next.date)}` : '—'}</span>
          </div>
        </div>
      )}

      {rules.isSuccess && rules.data.length === 0 && (
        <EmptyState
          title="Sin movimientos recurrentes"
          message="Automatiza tu arriendo, suscripciones o nómina para no olvidarlos."
          icon={<Repeat size={22} aria-hidden="true" />}
        />
      )}

      {rules.isSuccess && rules.data.length > 0 && (
        <ul className="divide-y divide-line-soft rounded-[18px] bg-surface px-4 py-1">
          {rules.data.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => {
                  setEditing(r);
                  setFormOpen(true);
                }}
                aria-label={`Editar recurrente ${r.note || catMap.get(r.category_id) || ''}`}
                className={cn('flex min-h-[60px] w-full items-center gap-3 py-3 text-left', !r.active && 'opacity-60')}
              >
                <span
                  aria-hidden="true"
                  className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px]', r.type === 'income' ? 'bg-income-tint text-income' : 'bg-expense-tint text-[#9A3412]')}
                >
                  <Repeat size={18} />
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-sm font-semibold">{r.note || catMap.get(r.category_id) || 'Recurrente'}</span>
                  <span className="truncate text-xs text-muted">{ruleMeta(r, accMap.get(r.account_id))}</span>
                </span>
                <Money value={r.amount} type={r.type} className="text-sm font-bold" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {run.isSuccess && (
        <p role="status" className="rounded-ctl bg-primary-tint px-3 py-2 text-sm text-primary-hover">
          {run.data.created === 0
            ? 'No había movimientos pendientes.'
            : `Se ${run.data.created === 1 ? 'creó 1 movimiento' : `crearon ${run.data.created} movimientos`}.`}
        </p>
      )}
      {run.isError && (
        <p role="alert" className="rounded-ctl bg-expense-tint px-3 py-2 text-sm text-danger-ink">
          {errorMessage(run.error)}
        </p>
      )}

      {rules.isSuccess && rules.data.length > 0 && (
        <Button variant="secondary" block loading={run.isPending} onClick={() => run.mutate()}>
          <Play size={16} aria-hidden="true" />
          Ejecutar pendientes
        </Button>
      )}

      {upcoming.data && upcoming.data.length > 0 && (
        <section aria-label="Próximos 30 días" className="rounded-[18px] bg-surface px-4 py-3">
          <h2 className="pb-1 text-sm font-bold">Próximos 30 días</h2>
          <ul className="divide-y divide-line-soft">
            {upcoming.data.slice(0, 8).map((u, i) => (
              <li key={`${u.rule_id}-${u.date}-${i}`} className="flex min-h-[44px] items-center justify-between gap-3 text-sm">
                <span className="min-w-0 truncate">
                  <span className="font-semibold">{u.note || catMap.get(u.category_id) || 'Recurrente'}</span>
                  <span className="text-muted"> · {shortDate(u.date)}</span>
                </span>
                <Money value={u.amount} type={u.type} className="font-bold" />
              </li>
            ))}
          </ul>
        </section>
      )}

      <Button
        size="lg"
        block
        onClick={() => {
          setEditing(null);
          setFormOpen(true);
        }}
      >
        Nuevo recurrente
      </Button>

      <RecurringFormSheet open={formOpen} onOpenChange={setFormOpen} rule={editing} />
    </div>
  );
}
