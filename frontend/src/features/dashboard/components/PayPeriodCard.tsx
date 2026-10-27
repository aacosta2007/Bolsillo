import { Link } from 'react-router-dom';
import { TrendingUp } from 'lucide-react';
import { rangeLabel, weekdayDate } from '@/shared/lib/dates';
import { formatMoney, formatMoneyWhole, formatPercent, toCents } from '@/shared/lib/money';
import { cn } from '@/shared/ui';
import type { PayPeriod } from '../../reports/types';
import type { NextPayday } from '../types';

const clamp = (n: number) => Math.max(0, Math.min(100, n));

/** Tarjeta principal del Inicio: cuánto te queda de esta quincena y a qué ritmo. */
export function PayPeriodCard({ period, nextPayday }: { period: PayPeriod; nextPayday: NextPayday | null }) {
  const isCalendar = period.source === 'calendar';
  const netCents = toCents(period.net);
  // Disponible nunca negativo; con net <= 0 tampoco hay "por día".
  const available = netCents > 0n ? period.net : '0';
  const perDay = netCents > 0n && period.available_per_day ? period.available_per_day : '0';
  const range = rangeLabel(period.start, period.end);
  const hasExtra = !isCalendar && toCents(period.extra_income) > 0n;

  return (
    <section aria-label="Esta quincena" className="flex flex-col gap-3.5 rounded-xl2 bg-primary p-5 text-white">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] text-[#CFE6E1]">{isCalendar ? `Quincena de calendario · ${range}` : `Esta quincena · ${range}`}</span>
        <span className="rounded-full bg-white/[0.16] px-2.5 py-1 text-xs font-bold">
          Día {period.days_elapsed} de {period.days}
        </span>
      </div>

      <div className="flex flex-col gap-0.5">
        <span className="text-[13px] text-[#CFE6E1]">
          Te quedan para {period.days_remaining} {period.days_remaining === 1 ? 'día' : 'días'}
        </span>
        <span className="tnum font-display text-[38px] font-bold tracking-[-0.5px]">{formatMoney(available)}</span>
        <span className="text-sm text-[#E6F2EF]">
          ≈ <strong className="text-white">{formatMoneyWhole(perDay)} por día</strong>
          {nextPayday ? ` hasta tu próximo pago (${weekdayDate(nextPayday.date)})` : ` hasta que termine la quincena`}
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="relative h-3 rounded-full bg-white/[0.18]">
          <div
            role="progressbar"
            aria-label="Gastado de lo recibido"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(clamp(period.spent_percent))}
            className="h-full rounded-full bg-[#F2A65A]"
            style={{ width: `${clamp(period.spent_percent)}%` }}
          />
          <div
            data-testid="time-marker"
            aria-hidden="true"
            className="absolute -top-1 h-5 w-0.5 rounded-sm bg-white"
            style={{ left: `${clamp(period.time_percent)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-[#CFE6E1]">
          <span>Gastado {formatPercent(period.spent_percent, 0)}</span>
          <span>Tiempo transcurrido {formatPercent(period.time_percent, 0)}</span>
        </div>
      </div>

      {netCents < 0n && (
        <span className="text-[13px] font-semibold text-[#FFD9B8]">
          Gastaste {formatMoney(period.net.replace('-', ''))} más de lo que recibiste
        </span>
      )}

      <div className={cn('grid gap-2', hasExtra ? 'grid-cols-3' : 'grid-cols-2')}>
        {isCalendar ? (
          <Stat label="Recibido" value={formatMoney(period.income)} />
        ) : (
          <>
            <Stat label="Sueldo" value={formatMoney(period.salary_income)} />
            {hasExtra && <Stat label="Extra" value={formatMoney(period.extra_income)} />}
          </>
        )}
        <Stat label="Gastado" value={formatMoney(period.expense)} />
      </div>

      {isCalendar && (
        <p role="note" className="rounded-ctl2 bg-white/[0.12] p-3 text-[13px] leading-[1.4] text-[#E6F2EF]">
          Aún no hay un sueldo registrado en este periodo: los números incluyen cualquier ingreso.{' '}
          <Link to="/metas?tab=recurrentes" className="font-semibold text-white underline underline-offset-2">
            Marca tu sueldo en Metas → Recurrentes
          </Link>
        </p>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5 rounded-ctl2 bg-white/[0.12] p-2.5">
      <span className="text-xs text-[#CFE6E1]">{label}</span>
      <span className="tnum truncate text-[15px] font-bold">{value}</span>
    </div>
  );
}

/** Aviso de ritmo bajo la tarjeta: solo si vas más rápido que el tiempo; si vas bien, uno discreto. */
export function PaceNotice({ period, previous }: { period: PayPeriod; previous: PayPeriod | null }) {
  const fast = period.spent_percent > period.time_percent + 5;
  if (fast) {
    const prevPerDay = previous?.spent_per_day;
    return (
      <div role="status" className="flex items-center gap-3 rounded-2xl border border-[#F5D3AE] bg-[#FFF4E8] px-3.5 py-3">
        <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-[#C2410C] text-white">
          <TrendingUp size={18} />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="text-sm font-semibold text-[#7A2A08]">Vas un poco más rápido que el tiempo</span>
          <span className="text-[13px] text-[#8A4A26]">
            {prevPerDay ? `La quincena pasada gastaste ${formatMoneyWhole(prevPerDay)}/día; esta vas en ` : 'Esta quincena vas en '}
            {period.spent_per_day ? `${formatMoneyWhole(period.spent_per_day)}/día` : 'un ritmo alto'}
          </span>
        </div>
      </div>
    );
  }
  if (toCents(period.income) > 0n && period.spent_percent <= period.time_percent) {
    return (
      <p role="status" className="px-1 text-[13px] text-muted">
        Vas con buen ritmo: has gastado menos de lo que avanzó la quincena.
      </p>
    );
  }
  return null;
}
