import { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { currentMonth, daysLeftInMonth, monthName, shiftMonth, todayISO } from '@/shared/lib/dates';
import { formatMoney, fromCents, percentOf, sumMoney, toCents } from '@/shared/lib/money';
import {
  Button, EmptyState, ErrorState, IconBadge, IconButton, ListSkeleton, MonthSwitcher, PageHeader, ProgressBar, Skeleton, StatusChip, errorMessage,
} from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { useCategories } from '@/features/categories/hooks';
import { useBudgets, useCopyBudgets } from '../hooks';
import { BudgetFormSheet } from '../components/BudgetFormSheet';
import type { BudgetState, BudgetStatus } from '../types';

const BAR: Record<BudgetState, string> = { ok: '#0F5E55', warning: '#E58A2E', exceeded: '#B33A0A' };

export function BudgetsPage() {
  const { user } = useAuth();
  const tz = user?.timezone;
  const nowMonth = currentMonth(tz);
  const [month, setMonth] = useState(nowMonth);
  const budgets = useBudgets(month);
  const cats = useCategories();
  const copy = useCopyBudgets();
  const [editing, setEditing] = useState<BudgetStatus | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const catMap = useMemo(() => new Map((cats.data ?? []).map((c) => [c.id, c])), [cats.data]);
  const list = useMemo(() => budgets.data ?? [], [budgets.data]);
  const used = useMemo(() => new Set(list.map((b) => b.category_id)), [list]);

  const totals = useMemo(() => {
    const spent = sumMoney(list.map((b) => b.spent));
    const limit = sumMoney(list.map((b) => b.amount_limit));
    return { spent, limit, percent: percentOf(spent, limit) };
  }, [list]);

  const isCurrent = month === nowMonth;
  const daysLeft = isCurrent ? daysLeftInMonth(todayISO(tz)) : 0;
  const leftCents = toCents(totals.limit) - toCents(totals.spent);
  const perDay = daysLeft > 0 && leftCents > 0n ? fromCents((leftCents / BigInt(daysLeft) / 100n) * 100n) : null; // pesos enteros, redondeado hacia abajo

  const openNew = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const prev = shiftMonth(month, -1);

  return (
    <div className="flex flex-col gap-4 px-5 pb-6 pt-5">
      <PageHeader
        title="Presupuestos"
        actions={
          <IconButton label="Nuevo presupuesto" variant="primary" onClick={openNew}>
            <Plus size={20} strokeWidth={2.4} aria-hidden="true" />
          </IconButton>
        }
      />
      <MonthSwitcher month={month} onChange={setMonth} />

      {budgets.isLoading && (
        <div role="status" aria-label="Cargando presupuestos" className="flex flex-col gap-4">
          <Skeleton className="h-[160px] rounded-[22px]" />
          <ListSkeleton rows={3} />
        </div>
      )}
      {budgets.isError && <ErrorState error={budgets.error} onRetry={() => budgets.refetch()} />}

      {budgets.isSuccess && list.length > 0 && (
        <section aria-label="Total presupuestado" className="flex flex-col gap-3 rounded-[22px] bg-ink p-[18px] text-white">
          <div className="flex items-baseline justify-between">
            <span className="text-[13px] text-[#C4CEC8]">Gastado del total presupuestado</span>
            {isCurrent && <span className="text-[13px] text-[#C4CEC8]">{daysLeft} {daysLeft === 1 ? 'día restante' : 'días restantes'}</span>}
          </div>
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="tnum font-display text-[30px] font-bold">{formatMoney(totals.spent)}</span>
            <span className="text-sm text-[#C4CEC8]">de {formatMoney(totals.limit)}</span>
          </div>
          <ProgressBar percent={totals.percent} color="#7DD3C0" trackClass="bg-[#34403A]" height={10} label="Porcentaje gastado del total" />
          <span className="text-[13px] text-[#C4CEC8]">
            {leftCents < 0n
              ? `Te pasaste por ${formatMoney(fromCents(-leftCents))} del total presupuestado.`
              : perDay
                ? `Puedes gastar ≈ ${formatMoney(perDay)} por día y cerrar el mes en verde.`
                : 'Presupuesto del mes completo.'}
          </span>
        </section>
      )}

      {budgets.isSuccess && list.length === 0 && (
        <EmptyState
          title="Sin presupuestos este mes"
          message="Define un límite por categoría para controlar tus gastos."
          action={<Button onClick={openNew}>Crear presupuesto</Button>}
        />
      )}

      <ul className="flex flex-col gap-2.5">
        {list.map((b) => {
          const cat = catMap.get(b.category_id);
          const overBy = b.status === 'exceeded' ? formatMoney(b.remaining.replace('-', '')) : null;
          const note = overBy
            ? `Te pasaste por ${overBy}`
            : toCents(b.remaining) === 0n
              ? 'Presupuesto completo'
              : `Disponible ${formatMoney(b.remaining)}`;
          const tone = b.status === 'exceeded' ? 'danger' : b.status === 'warning' ? 'warning' : 'ok';
          return (
            <li key={b.id}>
              <button
                type="button"
                onClick={() => {
                  setEditing(b);
                  setFormOpen(true);
                }}
                aria-label={`Editar presupuesto de ${cat?.name ?? 'categoría'}`}
                className="flex w-full flex-col gap-2.5 rounded-[18px] bg-surface px-4 py-3.5 text-left"
              >
                <span className="flex items-center gap-2.5">
                  <IconBadge icon={cat?.icon} color={cat?.color} size={34} rounded={10} />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-[15px] font-semibold">{cat?.name ?? 'Categoría'}</span>
                    <span className="tnum text-xs text-muted">
                      {formatMoney(b.spent)} de {formatMoney(b.amount_limit)}
                    </span>
                  </span>
                  <StatusChip tone={tone}>{Math.round(b.percent)} %</StatusChip>
                </span>
                <ProgressBar percent={b.percent} color={BAR[b.status]} label={`${cat?.name ?? 'Presupuesto'}: ${Math.round(b.percent)} por ciento`} />
                <span className={`tnum text-xs ${b.status === 'exceeded' ? 'text-expense' : 'text-muted'}`}>{note}</span>
              </button>
            </li>
          );
        })}
      </ul>

      {budgets.isSuccess && (
        <>
          {copy.isError && (
            <p role="alert" className="rounded-ctl bg-expense-tint px-3 py-2 text-sm text-danger-ink">
              {errorMessage(copy.error)}
            </p>
          )}
          {copy.isSuccess && (
            <p role="status" className="rounded-ctl bg-primary-tint px-3 py-2 text-sm text-primary-hover">
              {copy.data.length === 0 ? 'No había presupuestos nuevos para copiar.' : 'Presupuestos copiados.'}
            </p>
          )}
          <Button variant="dashed" loading={copy.isPending} onClick={() => copy.mutate({ from: prev, to: month })}>
            Copiar presupuestos de {monthName(prev)}
          </Button>
        </>
      )}

      <BudgetFormSheet
        open={formOpen}
        onOpenChange={setFormOpen}
        month={month}
        budget={editing}
        categories={cats.data ?? []}
        usedCategoryIds={used}
      />
    </div>
  );
}
