import { rangeLabel } from '@/shared/lib/dates';
import { formatMoney, formatMoneyWhole } from '@/shared/lib/money';
import type { PayPeriod } from '../types';
import { payPeriodHighlights } from '../summary';

/** Texto resumen calculado en cliente sobre las quincenas cerradas. */
export function PayPeriodsSummary({ periods }: { periods: PayPeriod[] }) {
  const { best, deficit, longest } = payPeriodHighlights(periods);
  if (!best && !deficit && !longest) return null;
  return (
    <p className="rounded-2xl bg-primary-tint px-4 py-3.5 text-sm leading-[1.45] text-primary-hover">
      {best && (
        <>
          Tu mejor quincena fue la del <strong>{rangeLabel(best.start, best.end)}</strong>
          {best.spent_per_day ? <>: gastaste {formatMoneyWhole(best.spent_per_day)} por día y </> : <>: </>}
          sobraron {formatMoney(best.net)}.{' '}
        </>
      )}
      {deficit && (
        <>
          La del <strong>{rangeLabel(deficit.start, deficit.end)}</strong> cerró en rojo ({formatMoney(deficit.net)}).{' '}
        </>
      )}
      {longest && (
        <>
          La del <strong>{rangeLabel(longest.start, longest.end)}</strong> duró {longest.days} días.
        </>
      )}
    </p>
  );
}
