import { ChevronLeft, ChevronRight } from 'lucide-react';
import { monthLabel, shiftMonth } from '../lib/dates';

export function MonthSwitcher({
  month,
  onChange,
  maxMonth,
}: {
  month: string;
  onChange: (m: string) => void;
  /** Último mes seleccionable (no permite avanzar más allá). */
  maxMonth?: string;
}) {
  const atMax = maxMonth !== undefined && month >= maxMonth;
  return (
    <div className="flex items-center justify-between rounded-ctl2 bg-surface p-1">
      <button
        type="button"
        aria-label="Mes anterior"
        onClick={() => onChange(shiftMonth(month, -1))}
        className="flex h-11 w-11 items-center justify-center rounded-[10px] hover:bg-bg"
      >
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
      <span aria-live="polite" className="text-[15px] font-bold">
        {monthLabel(month)}
      </span>
      <button
        type="button"
        aria-label="Mes siguiente"
        disabled={atMax}
        onClick={() => onChange(shiftMonth(month, 1))}
        className="flex h-11 w-11 items-center justify-center rounded-[10px] hover:bg-bg disabled:opacity-30 disabled:hover:bg-transparent"
      >
        <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
