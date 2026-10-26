import { Cell, Pie, PieChart } from 'recharts';
import type { BudgetStatus } from '@/features/budgets/types';
import { daysBetween, rangeLabel, shortDate } from '@/shared/lib/dates';
import { formatMoney, formatMoneyWhole, toCents } from '@/shared/lib/money';
import { Card, CardHeader, ProgressBar, StatusChip, cn } from '@/shared/ui';
import { describeChange, describePoints, TONE_CLASS, type Change } from '../monthly';
import type { MonthlyCategory, MonthlyDay, MonthlyGoal, MonthlyGoalStatus, MonthlyReport, PayPeriod } from '../types';

const FALLBACK_COLOR = '#8A968F';

/** Variación con texto accesible: el símbolo y el color se complementan con texto para lectores de pantalla. */
export function ChangeText({ change, vs, className }: { change: Change; vs?: string; className?: string }) {
  return (
    <span className={cn('font-bold', TONE_CLASS[change.tone], className)}>
      <span aria-hidden="true">{change.text}</span>
      <span className="sr-only">
        {change.sr}
        {vs ? ` frente a ${vs}` : ''}
      </span>
    </span>
  );
}

const fmtRate = (n: number) => `${n.toFixed(1).replace(/\.0$/, '').replace('.', ',')} %`;

// ---------- KPIs ----------
export function Kpis({ report, prevName }: { report: MonthlyReport; prevName: string }) {
  const s = report.summary;
  const items: Array<{ label: string; value: string; color: string; change: Change | null }> = [
    { label: 'Ingresos', value: formatMoney(s.income), color: 'text-income', change: describeChange(s.income_change_pct, 'income') },
    { label: 'Gastos', value: formatMoney(s.expense), color: 'text-expense', change: describeChange(s.expense_change_pct, 'expense') },
    { label: 'Ahorro', value: formatMoney(s.net), color: toCents(s.net) < 0n ? 'text-expense' : 'text-primary', change: describeChange(s.net_change_pct, 'income') },
    {
      label: 'Tasa de ahorro',
      value: s.savings_rate === null ? '—' : fmtRate(s.savings_rate),
      color: 'text-ink',
      change: describePoints(s.savings_rate, s.prev?.savings_rate),
    },
  ];
  return (
    <section aria-label="Resumen del mes" className="grid grid-cols-2 gap-2">
      {items.map((k) => (
        <div key={k.label} className="flex flex-col gap-0.5 rounded-[16px] bg-surface px-3.5 py-3">
          <span className="text-xs text-muted">{k.label}</span>
          <span className={cn('tnum font-display text-xl font-bold', k.color)}>{k.value}</span>
          <span className="text-xs">
            {k.change ? (
              <>
                <ChangeText change={k.change} vs={prevName} /> <span className="text-muted">vs {prevName.slice(0, 3)}</span>
              </>
            ) : (
              <span className="text-muted">sin datos del mes anterior</span>
            )}
          </span>
        </div>
      ))}
    </section>
  );
}

// ---------- Observaciones ----------
const DOT: Record<string, string> = { positive: '#5CC9A7', warning: '#F0A04B', neutral: '#9AA7A0' };

export function Insights({ report, monthName }: { report: MonthlyReport; monthName: string }) {
  if (report.insights.length === 0) return null;
  return (
    <section aria-label={`Lo que pasó en ${monthName}`} className="flex flex-col gap-2.5 rounded-card bg-ink px-[18px] py-4 text-white">
      <h2 className="text-[15px] font-bold">Lo que pasó en {monthName}</h2>
      <ul className="flex flex-col gap-2.5">
        {report.insights.map((i, idx) => (
          <li key={idx} className="flex items-start gap-2.5 text-sm leading-snug">
            <span data-tone={i.tone} aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: DOT[i.tone] ?? DOT.neutral }} />
            <span className="text-[#E3E8E5]">{i.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---------- Gastos por categoría ----------
function CategoryRow({ c, maxTotal, prevName, kind }: { c: MonthlyCategory; maxTotal: number; prevName: string; kind: 'expense' | 'income' }) {
  const isNew = kind === 'income' ? !!c.is_new : c.change_pct === null && toCents(c.total) > 0n;
  const change = describeChange(c.change_pct, kind, isNew);
  const color = c.color ?? FALLBACK_COLOR;
  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2 text-sm">
        <span aria-hidden="true" className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: color }} />
        <span className="min-w-0 flex-1 truncate font-semibold">{c.name}</span>
        <span className="tnum">{formatMoney(c.total)}</span>
        <span className="w-[62px] text-right text-xs">{change && <ChangeText change={change} vs={prevName} />}</span>
      </div>
      <ProgressBar percent={(Number(c.total) / maxTotal) * 100} color={color} height={6} label={`${c.name}: ${Math.round(c.percent)} % del gasto del mes`} />
    </li>
  );
}

export function ExpenseByCategory({ report, prevName }: { report: MonthlyReport; prevName: string }) {
  const cats = report.expense_by_category;
  if (cats.length === 0) return null;
  const withSpend = cats.filter((c) => toCents(c.total) > 0n);
  const maxTotal = Math.max(1, ...cats.map((c) => Number(c.total)));
  const summary = withSpend
    .slice(0, 5)
    .map((c) => `${c.name} ${Math.round(c.percent)} %`)
    .join(', ');
  return (
    <Card className="flex flex-col gap-3">
      <CardHeader title="Gastos por categoría" aside={`vs ${prevName}`} />
      {withSpend.length > 0 && (
        <div className="flex items-center gap-4">
          <div role="img" aria-label={`Distribución del gasto: ${summary}`} className="shrink-0">
            <PieChart width={104} height={104}>
              <Pie
                data={withSpend.map((c) => ({ name: c.name, value: Number(c.total) }))}
                dataKey="value"
                innerRadius={30}
                outerRadius={50}
                paddingAngle={1}
                stroke="none"
                isAnimationActive={false}
              >
                {withSpend.map((c) => (
                  <Cell key={c.category_id} fill={c.color ?? FALLBACK_COLOR} />
                ))}
              </Pie>
            </PieChart>
          </div>
          <div className="flex min-w-0 flex-col gap-0.5 text-[13px]">
            <span className="text-muted">Total gastado</span>
            <span className="tnum font-display text-xl font-bold">{formatMoney(report.summary.expense)}</span>
            <span className="text-muted">
              {withSpend.length} {withSpend.length === 1 ? 'categoría' : 'categorías'}
            </span>
          </div>
        </div>
      )}
      <ul aria-label="Gasto por categoría" className="flex flex-col gap-3">
        {cats.map((c) => (
          <CategoryRow key={c.category_id} c={c} maxTotal={maxTotal} prevName={prevName} kind="expense" />
        ))}
      </ul>
    </Card>
  );
}

// ---------- Ingresos por fuente ----------
export function IncomeBySource({ report, prevName }: { report: MonthlyReport; prevName: string }) {
  const rows = report.income_by_category;
  if (rows.length === 0) return null;
  return (
    <Card>
      <CardHeader title="Ingresos por fuente" aside={`vs ${prevName}`} />
      <ul aria-label="Ingresos por fuente" className="flex flex-col gap-2.5">
        {rows.map((c) => {
          const change = describeChange(c.change_pct, 'income', !!c.is_new);
          return (
            <li key={c.category_id} className="flex items-center gap-2.5 text-sm">
              <span className="min-w-0 flex-1 truncate font-semibold">{c.name}</span>
              <span className="tnum">{formatMoney(c.total)}</span>
              <span className="w-[62px] text-right text-xs">
                {change ? <ChangeText change={change} vs={prevName} className={change.text === 'nuevo' ? 'text-income' : undefined} /> : null}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

// ---------- Top 5 ----------
export function TopExpenses({ report }: { report: MonthlyReport }) {
  if (report.top_expenses.length === 0) return null;
  return (
    <Card>
      <CardHeader title="Tus 5 gastos más grandes" />
      <ol aria-label="Gastos más grandes" className="flex flex-col">
        {report.top_expenses.slice(0, 5).map((t, i, arr) => (
          <li key={t.transaction_id} className={cn('flex items-center gap-3 py-2.5', i < arr.length - 1 && 'border-b border-line-soft')}>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-sm font-semibold">{t.note || t.category}</span>
              <span className="truncate text-xs text-muted">
                {shortDate(t.date)} · {t.category} · {t.account}
              </span>
            </div>
            <span className="tnum text-sm font-bold text-expense">{formatMoney(t.amount)}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

// ---------- Día a día ----------
export function DailySpending({ report }: { report: MonthlyReport }) {
  const days: MonthlyDay[] = report.daily;
  if (days.length === 0) return null;
  const max = Math.max(1, ...days.map((d) => Number(d.expense)));
  const st = report.daily_stats;
  const paydays = days.filter((d) => d.is_payday).length;
  const label =
    `Gasto día a día: ${days.length} días, el día de mayor gasto fue ${st.max_day ? shortDate(st.max_day) : 'ninguno'} con ${formatMoneyWhole(st.max_day_expense)}` +
    (paydays ? `, ${paydays} ${paydays === 1 ? 'día de pago resaltado' : 'días de pago resaltados'}` : '');
  const facts: Array<[string, string]> = [
    ['Día de mayor gasto', st.max_day ? `${shortDate(st.max_day)} · ${formatMoneyWhole(st.max_day_expense)}` : '—'],
    ['Promedio diario', formatMoneyWhole(st.avg_daily_expense)],
    ['Días sin gastar', String(st.no_spend_days)],
  ];
  return (
    <Card className="flex flex-col gap-3">
      <CardHeader title="Gasto día a día" aside={paydays ? <span className="text-income">▮ día de pago</span> : undefined} />
      <div role="img" aria-label={label} className="flex h-[72px] items-end gap-[2px]">
        {days.map((d) => {
          const spent = Number(d.expense);
          const h = spent > 0 ? Math.max(4, (spent / max) * 72) : 2;
          return <span key={d.date} className={cn('flex-1 rounded-t-[2px]', d.is_payday ? 'bg-income' : spent > 0 ? 'bg-expense/70' : 'bg-line')} style={{ height: h }} />;
        })}
      </div>
      <dl className="grid grid-cols-3 gap-2">
        {facts.map(([k, v]) => (
          <div key={k} className="flex flex-col gap-0.5 rounded-ctl bg-bg px-2.5 py-2">
            <dt className="text-[11px] text-muted">{k}</dt>
            <dd className="tnum text-[13px] font-bold">{v}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

// ---------- Quincenas del mes ----------
function PeriodCard({ p }: { p: PayPeriod }) {
  const net = toCents(p.net);
  const headline = p.in_progress
    ? `Disponible ${formatMoney(p.net)}`
    : net >= 0n
      ? `Sobraron ${formatMoney(p.net)}`
      : `Faltaron ${formatMoney(p.net.replace('-', ''))}`;
  const meta = `${rangeLabel(p.start, p.end)} · ${p.in_progress ? 'en curso' : `${p.days || daysBetween(p.start, p.end) + 1} días`}`;
  return (
    <li className="flex flex-col gap-1 rounded-[14px] border border-line p-3">
      <span className="text-xs text-muted">{meta}</span>
      <span className={cn('text-[15px] font-bold', net < 0n && 'text-expense')}>{headline}</span>
      {p.spent_per_day && <span className="text-xs text-muted">{formatMoneyWhole(p.spent_per_day)} por día</span>}
    </li>
  );
}

export function MonthPeriods({ report, monthName }: { report: MonthlyReport; monthName: string }) {
  if (report.pay_periods.length === 0) return null;
  return (
    <Card>
      <CardHeader title={`Tus quincenas de ${monthName}`} />
      <ul aria-label="Quincenas del mes" className="grid grid-cols-2 gap-2">
        {report.pay_periods.map((p) => (
          <PeriodCard key={p.start} p={p} />
        ))}
      </ul>
    </Card>
  );
}

// ---------- Presupuestos y metas ----------
const GOAL_STATUS: Record<MonthlyGoalStatus, { label: string; cls: string }> = {
  on_track: { label: 'Vas bien', cls: 'text-primary' },
  behind: { label: 'Atrasada', cls: 'text-[#9A3412]' },
  completed: { label: 'Completada', cls: 'text-primary' },
  no_target_date: { label: 'Sin fecha', cls: 'text-muted' },
};

const SEVERITY = { exceeded: 0, warning: 1, ok: 2 } as const;

function BudgetRow({ b, name }: { b: BudgetStatus; name: string }) {
  const color = b.status === 'exceeded' ? '#B33A0A' : b.status === 'warning' ? '#E58A2E' : '#0F5E55';
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-center gap-2 text-sm">
        <span className="min-w-0 flex-1 truncate font-semibold">{name}</span>
        <span className="tnum text-xs text-muted">
          {formatMoneyWhole(b.spent)} de {formatMoneyWhole(b.amount_limit)}
        </span>
      </div>
      <ProgressBar percent={b.percent} color={color} height={6} label={`${name}: ${Math.round(b.percent)} % del presupuesto`} />
    </li>
  );
}

function GoalRow({ g }: { g: MonthlyGoal }) {
  const st = GOAL_STATUS[g.status];
  const contributed = toCents(g.contributed_this_month) > 0n ? `aportaste ${formatMoney(g.contributed_this_month)}` : 'sin aportes';
  return (
    <li className="flex items-center gap-2.5 text-sm">
      <span className="min-w-0 flex-1">
        {g.name} · <span className="text-muted">{contributed}</span>
      </span>
      <span className={cn('font-bold', st.cls)}>{st.label}</span>
    </li>
  );
}

export function BudgetsAndGoals({ report, nameOf }: { report: MonthlyReport; nameOf: (categoryId: string) => string }) {
  const bs = report.budgets_summary;
  const hasBudgets = report.budgets.length > 0;
  if (!hasBudgets && report.goals.length === 0) return null;
  const budgets = [...report.budgets].sort((a, b) => SEVERITY[a.status] - SEVERITY[b.status] || b.percent - a.percent).slice(0, 4);
  return (
    <Card className="flex flex-col gap-3">
      <h2 className="text-base font-bold">Presupuestos y metas</h2>
      {hasBudgets && (
        <>
          <div className="flex flex-wrap gap-2">
            <StatusChip tone="ok">
              {bs.ok} {bs.ok === 1 ? 'cumplido' : 'cumplidos'}
            </StatusChip>
            <StatusChip tone="warning">{bs.warning} en riesgo</StatusChip>
            <StatusChip tone="danger">
              {bs.exceeded} {bs.exceeded === 1 ? 'excedido' : 'excedidos'}
            </StatusChip>
          </div>
          <ul aria-label="Presupuestos" className="flex flex-col gap-2.5">
            {budgets.map((b) => (
              <BudgetRow key={b.id} b={b} name={nameOf(b.category_id)} />
            ))}
          </ul>
        </>
      )}
      {report.goals.length > 0 && (
        <ul aria-label="Metas" className={cn('flex flex-col gap-2', hasBudgets && 'border-t border-line-soft pt-3')}>
          {report.goals.map((g) => (
            <GoalRow key={g.id} g={g} />
          ))}
        </ul>
      )}
    </Card>
  );
}
