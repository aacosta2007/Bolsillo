import { rangeLabel } from '@/shared/lib/dates';
import { formatMoney, formatMoneyWhole, toCents } from '@/shared/lib/money';
import { cn } from '@/shared/ui';
import type { PayPeriod, PayPeriodStatus } from '../types';

const STATUS_CHIP: Record<PayPeriodStatus, { label: string; cls: string }> = {
  en_curso: { label: 'en curso', cls: 'bg-[#E4ECFD] text-[#1E3A8A]' },
  ahorro: { label: 'ahorro', cls: 'bg-[#E3F0ED] text-[#0B4740]' },
  justo: { label: 'justo', cls: 'bg-[#FFF0DC] text-[#8A4A0F]' },
  deficit: { label: 'déficit', cls: 'bg-[#FDE3D6] text-[#8A2C07]' },
};

/** "+ $ 97.900", "− $ 80.000" o "$ 0". */
export function formatNet(net: string): string {
  const c = toCents(net);
  if (c === 0n) return formatMoney('0');
  return c < 0n ? formatMoney(net) : `+ ${formatMoney(net)}`;
}

function PeriodRow({ p, last }: { p: PayPeriod; last: boolean }) {
  const chip = STATUS_CHIP[p.status];
  const negative = toCents(p.net) < 0n;
  const meta = [
    p.in_progress ? `día ${p.days_elapsed} de ${p.days}` : `${p.days} días`,
    `gastaste ${formatMoney(p.expense)}`,
    p.spent_per_day ? `${formatMoneyWhole(p.spent_per_day)}/día` : null,
  ]
    .filter(Boolean)
    .join(' · ');
  return (
    <li className={cn('flex items-center gap-3 py-3', !last && 'border-b border-line-soft')}>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-sm font-semibold">{rangeLabel(p.start, p.end)}</span>
        <span className="text-xs text-muted">{meta}</span>
      </div>
      <div className="flex flex-col items-end gap-0.5">
        <span className={cn('tnum text-sm font-bold', negative ? 'text-expense' : 'text-primary')}>{formatNet(p.net)}</span>
        <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-bold', chip.cls)}>{chip.label}</span>
      </div>
    </li>
  );
}

/** Lista de periodos, de la más reciente a la más antigua. */
export function PayPeriodsList({ periods }: { periods: PayPeriod[] }) {
  return (
    <ul aria-label="Quincenas" className="rounded-card bg-surface px-[18px] py-1">
      {periods.map((p, i) => (
        <PeriodRow key={p.start} p={p} last={i === periods.length - 1} />
      ))}
    </ul>
  );
}
