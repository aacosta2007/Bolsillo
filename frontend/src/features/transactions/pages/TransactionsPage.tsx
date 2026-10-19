import { useEffect, useMemo, useRef, useState } from 'react';
import { Download, Search } from 'lucide-react';
import { currentMonth, dayLabel, monthEnd, monthStart, todayISO } from '@/shared/lib/dates';
import { saveBlob } from '@/shared/lib/download';
import { useDebounced } from '@/shared/lib/useDebounced';
import { Button, Chip, EmptyState, ErrorState, ListSkeleton, Money, MonthSwitcher, PageHeader, errorMessage } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { useDashboardSummary } from '@/features/dashboard/hooks';
import { transactionsApi } from '../api';
import { useTransactionsInfinite } from '../hooks';
import { useLookups } from '../lookups';
import { TransactionRow } from '../components/TransactionRow';
import { TransactionDetailSheet } from '../components/TransactionDetailSheet';
import type { Transaction, TransactionFilters, TxType } from '../types';

type Filter = 'all' | TxType;
const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: 'all', label: 'Todos' },
  { id: 'expense', label: 'Gastos' },
  { id: 'income', label: 'Ingresos' },
  { id: 'transfer', label: 'Transferencias' },
];

export function groupByDay(items: Transaction[]): Array<{ date: string; items: Transaction[] }> {
  const groups: Array<{ date: string; items: Transaction[] }> = [];
  for (const tx of items) {
    const last = groups[groups.length - 1];
    if (last && last.date === tx.date) last.items.push(tx);
    else groups.push({ date: tx.date, items: [tx] });
  }
  return groups;
}

export function TransactionsPage() {
  const { user } = useAuth();
  const tz = user?.timezone;
  const today = todayISO(tz);
  const [month, setMonth] = useState(() => currentMonth(tz));
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const q = useDebounced(search.trim(), 300);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const from = monthStart(month);
  const to = monthEnd(month);
  const filters = useMemo<TransactionFilters>(
    () => ({ from, to, type: filter === 'all' ? undefined : filter, q: q || undefined }),
    [from, to, filter, q],
  );

  const list = useTransactionsInfinite(filters);
  const summary = useDashboardSummary(from, to);
  const lookups = useLookups();
  const items = useMemo(() => list.data?.pages.flatMap((p) => p.items) ?? [], [list.data]);
  const groups = useMemo(() => groupByDay(items), [items]);

  // Scroll infinito con IntersectionObserver (+ botón de respaldo).
  const sentinel = useRef<HTMLDivElement>(null);
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = list;
  useEffect(() => {
    const el = sentinel.current;
    if (!el || !hasNextPage || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver((e) => {
      if (e[0]?.isIntersecting && !isFetchingNextPage) void fetchNextPage();
    });
    io.observe(el);
    return () => io.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const exportCsv = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const { blob, filename } = await transactionsApi.exportCsv(from, to);
      saveBlob(blob, filename ?? `bolsillo_${from}_${to}.csv`);
    } catch (e) {
      setExportError(errorMessage(e));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-3.5 px-5 pb-6 pt-5">
      <PageHeader
        title="Movimientos"
        actions={
          <Button variant="secondary" className="min-h-[44px] gap-1.5 px-3.5 text-[13px] font-semibold" onClick={exportCsv} loading={exporting} aria-label="Exportar CSV">
            <Download size={16} aria-hidden="true" />
            CSV
          </Button>
        }
      />
      {exportError && (
        <p role="alert" className="rounded-ctl bg-expense-tint px-3 py-2 text-sm text-danger-ink">
          No se pudo exportar: {exportError}
        </p>
      )}

      <label className="flex h-[46px] items-center gap-2.5 rounded-ctl2 border border-line bg-surface px-3.5 text-muted">
        <Search size={18} aria-hidden="true" />
        <span className="sr-only">Buscar movimientos</span>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nota…"
          className="flex-1 border-0 bg-transparent text-[15px] text-ink outline-none placeholder:text-muted/70"
        />
      </label>

      <div className="no-scrollbar -mx-5 flex gap-2 overflow-x-auto px-5">
        {FILTERS.map((f) => (
          <Chip key={f.id} active={filter === f.id} onClick={() => setFilter(f.id)}>
            {f.label}
          </Chip>
        ))}
      </div>

      <MonthSwitcher month={month} onChange={setMonth} />

      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col rounded-ctl2 bg-surface px-3 py-2.5">
          <span className="text-xs text-muted">Ingresos del mes</span>
          <span className="tnum font-bold text-income">{summary.data ? <Money value={summary.data.income} type="income" /> : '—'}</span>
        </div>
        <div className="flex flex-col rounded-ctl2 bg-surface px-3 py-2.5">
          <span className="text-xs text-muted">Gastos del mes</span>
          <span className="tnum font-bold text-expense">{summary.data ? <Money value={summary.data.expense} type="expense" /> : '—'}</span>
        </div>
      </div>

      {list.isLoading && <ListSkeleton rows={6} />}
      {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}

      {list.isSuccess && groups.length === 0 && (
        <EmptyState
          title={q || filter !== 'all' ? 'Sin resultados' : 'Sin movimientos este mes'}
          message={q || filter !== 'all' ? 'Prueba con otra búsqueda o quita los filtros.' : 'Cuando registres gastos o ingresos aparecerán aquí.'}
        />
      )}

      {groups.map((g) => (
        <section key={g.date} aria-label={dayLabel(g.date, today)} className="flex flex-col gap-1.5">
          <div className="flex justify-between px-1 text-[13px] text-muted">
            <h2 className="font-semibold">{dayLabel(g.date, today)}</h2>
            <span className="tnum">
              {g.items.length} {g.items.length === 1 ? 'movimiento' : 'movimientos'}
            </span>
          </div>
          <div className="divide-y divide-line-soft rounded-[18px] bg-surface px-3.5 py-1">
            {g.items.map((tx) => (
              <TransactionRow
                key={tx.id}
                tx={tx}
                categoryMap={lookups.categoryMap}
                accountMap={lookups.accountMap}
                onClick={() => setSelected(tx)}
              />
            ))}
          </div>
        </section>
      ))}

      {hasNextPage && (
        <div ref={sentinel} className="flex justify-center py-2">
          <Button variant="secondary" loading={isFetchingNextPage} onClick={() => fetchNextPage()}>
            Cargar más
          </Button>
        </div>
      )}

      <TransactionDetailSheet tx={selected} lookups={lookups} onClose={() => setSelected(null)} />
    </div>
  );
}
