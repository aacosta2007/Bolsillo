import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight, PieChart, Settings, TriangleAlert } from 'lucide-react';
import { daysLeftInMonth, monthLabel, shortDate, todayISO } from '@/shared/lib/dates';
import { formatMoney } from '@/shared/lib/money';
import { Card, CardHeader, EmptyState, ErrorState, IconButton, ListSkeleton, Money, Skeleton } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { NotificationBell } from '@/features/notifications/components/NotificationBell';
import { useLookups } from '@/features/transactions/lookups';
import { TransactionRow } from '@/features/transactions/components/TransactionRow';
import { useDashboardSummary } from '../hooks';
import { BalanceCard } from '../components/BalanceCard';
import { CategoryDonut } from '../components/CategoryDonut';
import { TrendChart } from '../components/TrendChart';
import { PaceNotice, PayPeriodCard } from '../components/PayPeriodCard';
import { BeforePayday } from '../components/BeforePayday';

export function DashboardPage() {
  const { user } = useAuth();
  const tz = user?.timezone;
  const navigate = useNavigate();
  const q = useDashboardSummary();
  const lookups = useLookups();
  const today = todayISO(tz);
  const data = q.data;
  const month = (data?.period.to ?? today).slice(0, 7);
  const risk = data?.budgets_at_risk[0];
  const riskCat = risk ? lookups.categoryMap.get(risk.category_id) : undefined;

  return (
    <div className="flex flex-col gap-[18px] px-5 pb-6 pt-5">
      <header className="flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm text-muted">{user?.display_name ? `Hola, ${user.display_name}` : 'Hola de nuevo'}</span>
          <span className="font-display text-[22px] font-bold">{monthLabel(month)}</span>
        </div>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <IconButton label="Ajustes" onClick={() => navigate('/ajustes')}>
            <Settings size={20} aria-hidden="true" />
          </IconButton>
        </div>
      </header>

      {q.isLoading && (
        <div role="status" aria-label="Cargando resumen" className="flex flex-col gap-[18px]">
          <Skeleton className="h-[300px] rounded-xl2" />
          <Skeleton className="h-[170px] rounded-xl2" />
          <Skeleton className="h-[180px] rounded-card" />
          <Skeleton className="h-[170px] rounded-card" />
          <ListSkeleton rows={3} />
        </div>
      )}

      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}

      {data && (
        <>
          {data.current_pay_period && (
            <>
              <PayPeriodCard period={data.current_pay_period} nextPayday={data.next_payday} />
              <PaceNotice period={data.current_pay_period} previous={data.previous_pay_period} />
            </>
          )}

          {data.next_payday && <BeforePayday nextPayday={data.next_payday} fallback={data.upcoming_recurring} />}

          <BalanceCard data={data} />

          <Link to="/presupuestos" className="flex min-h-[56px] items-center gap-3 rounded-2xl bg-surface px-4 py-3">
            <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-primary-tint text-primary">
              <PieChart size={18} />
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="text-sm font-semibold">Presupuestos del mes</span>
              <span className="text-xs text-muted">
                {data.budgets_at_risk.length === 0
                  ? 'Todo en orden'
                  : `${data.budgets_at_risk.length} ${data.budgets_at_risk.length === 1 ? 'en riesgo o excedido' : 'en riesgo o excedidos'}`}
              </span>
            </span>
            <ChevronRight size={18} aria-hidden="true" className="text-muted" />
          </Link>

          {risk && (
            <div
              role="status"
              className="flex items-center gap-3 rounded-2xl border border-[#F5D3AE] bg-[#FFF4E8] px-3.5 py-3"
            >
              <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-[#C2410C] text-white">
                <TriangleAlert size={18} />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="text-sm font-semibold text-[#7A2A08]">
                  {risk.status === 'exceeded'
                    ? `${riskCat?.name ?? 'Un presupuesto'} superó el presupuesto`
                    : `${riskCat?.name ?? 'Un presupuesto'} va en el ${Math.round(risk.percent)} % del presupuesto`}
                </span>
                <span className="text-[13px] text-[#8A4A26]">
                  {risk.status === 'exceeded'
                    ? `Te pasaste por ${formatMoney(risk.remaining.replace('-', ''))}`
                    : `Te quedan ${formatMoney(risk.remaining)} para ${daysLeftInMonth(today)} días`}
                </span>
              </div>
              <Link to="/presupuestos" className="flex min-h-[44px] items-center px-1 text-[13px] font-semibold text-[#9A3412]">
                Ver
              </Link>
            </div>
          )}

          <CategoryDonut rows={data.by_category} />
          <TrendChart points={data.monthly_trend} />

          {!data.next_payday && data.upcoming_recurring.length > 0 && (
            <Card>
              <CardHeader title="Próximos 7 días" aside={<Link to="/metas?tab=recurrentes" className="font-semibold text-primary">Ver recurrentes</Link>} />
              <ul className="flex flex-col">
                {data.upcoming_recurring.slice(0, 3).map((u, i) => (
                  <li key={`${u.rule_id}-${u.date}-${i}`} className="flex min-h-[44px] items-center justify-between gap-3 text-sm">
                    <span className="min-w-0 truncate">
                      <span className="font-semibold">{u.note || lookups.categoryMap.get(u.category_id)?.name || 'Recurrente'}</span>
                      <span className="text-muted"> · {shortDate(u.date)}</span>
                    </span>
                    <Money value={u.amount} type={u.type} className="font-bold" />
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card className="flex flex-col gap-1.5">
            <CardHeader title="Últimos movimientos" aside={<Link to="/movimientos" className="font-semibold text-primary">Ver todos</Link>} />
            {data.recent_transactions.length === 0 ? (
              <EmptyState title="Sin movimientos todavía" message="Registra tu primer gasto o ingreso con el botón +." />
            ) : (
              data.recent_transactions.map((tx) => (
                <TransactionRow
                  key={tx.id}
                  tx={tx}
                  categoryMap={lookups.categoryMap}
                  accountMap={lookups.accountMap}
                  onClick={() => navigate(`/movimientos/${tx.id}/editar`)}
                  trailingMeta={tx.date === today ? 'Hoy' : shortDate(tx.date)}
                />
              ))
            )}
          </Card>
        </>
      )}
    </div>
  );
}
