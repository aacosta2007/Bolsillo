import { ChevronLeft, ChevronRight } from 'lucide-react';
import { monthLabel, shiftMonth } from '../lib/dates';

export function MonthSwitcher({ month, onChange }: { month: string; onChange: (m: string) => void }) {
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
        onClick={() => onChange(shiftMonth(month, 1))}
        className="flex h-11 w-11 items-center justify-center rounded-[10px] hover:bg-bg"
      >
        <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
