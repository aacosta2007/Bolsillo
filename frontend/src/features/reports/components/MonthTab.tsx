import { CalendarDays } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useTimezone } from '@/features/auth/AuthContext';
import { useCategoryMap } from '@/features/categories/hooks';
import { currentMonth, monthLabel, monthName, shiftMonth } from '@/shared/lib/dates';
import { toCents } from '@/shared/lib/money';
import { EmptyState, ErrorState, ListSkeleton, MonthSwitcher, Skeleton } from '@/shared/ui';
import { useMonthlyReport } from '../hooks';
import { resolveReportMonth } from '../monthly';
import {
  BudgetsAndGoals,
  DailySpending,
  ExpenseByCategory,
  IncomeBySource,
  Insights,
  Kpis,
  MonthPeriods,
  TopExpenses,
} from './MonthSections';

export function MonthTab() {
  const [params, setParams] = useSearchParams();
  const tz = useTimezone();
  const month = resolveReportMonth(params.get('mes'), tz);
  const maxMonth = currentMonth(tz);
  const q = useMonthlyReport(month);
  const { map: catMap } = useCategoryMap();

  const setMonth = (m: string) => setParams({ tab: 'mes', mes: m }, { replace: true });
  const name = monthName(month);
  const prevName = monthName(shiftMonth(month, -1));

  const report = q.data;
  const nameOf = (id: string) => catMap.get(id)?.name ?? report?.expense_by_category.find((c) => c.category_id === id)?.name ?? 'Presupuesto';
  const empty =
    !!report && toCents(report.summary.income) === 0n && toCents(report.summary.expense) === 0n && report.expense_by_category.length === 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <MonthSwitcher month={month} onChange={setMonth} maxMonth={maxMonth} />
        {(report?.is_partial ?? month === maxMonth) && <p className="text-center text-xs font-semibold text-muted">Mes en curso · parcial</p>}
      </div>

      {q.isLoading && (
        <div role="status" aria-label="Cargando reporte" className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-2">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[84px] rounded-[16px]" />
            ))}
          </div>
          <Skeleton className="h-[140px] rounded-card" />
          <ListSkeleton rows={4} />
        </div>
      )}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {empty && (
        <EmptyState
          title={`Sin movimientos en ${monthLabel(month)}`}
          message="Cuando registres ingresos o gastos en este mes, aquí verás el resumen."
          icon={<CalendarDays size={22} aria-hidden="true" />}
        />
      )}
      {report && !empty && (
        <>
          <Kpis report={report} prevName={prevName} />
          <Insights report={report} monthName={name} />
          <ExpenseByCategory report={report} prevName={prevName} />
          <IncomeBySource report={report} prevName={prevName} />
          <TopExpenses report={report} />
          <DailySpending report={report} />
          <MonthPeriods report={report} monthName={name} />
          <BudgetsAndGoals report={report} nameOf={nameOf} />
        </>
      )}
    </div>
  );
}
