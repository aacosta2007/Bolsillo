import { toCents } from '@/shared/lib/money';
import type { PayPeriod } from './types';

export interface PayPeriodsHighlights {
  /** Quincena cerrada con mayor neto (solo si sobró dinero). */
  best: PayPeriod | null;
  /** Quincena cerrada en déficit con peor neto. */
  deficit: PayPeriod | null;
  /** Quincena cerrada más larga que las demás (ajuste de fin de semana). */
  longest: PayPeriod | null;
}

/** Calcula, sobre periodos cerrados, la mejor quincena y la más larga o en déficit. En empate gana la más reciente. */
export function payPeriodHighlights(periods: PayPeriod[]): PayPeriodsHighlights {
  const closed = periods.filter((p) => !p.in_progress);
  let best: PayPeriod | null = null;
  let deficit: PayPeriod | null = null;
  for (const p of closed) {
    const net = toCents(p.net);
    if (net > 0n && (!best || net > toCents(best.net))) best = p;
    if (net < 0n && (!deficit || net < toCents(deficit.net))) deficit = p;
  }
  let longest: PayPeriod | null = null;
  if (closed.length > 1) {
    const minDays = Math.min(...closed.map((p) => p.days));
    for (const p of closed) {
      if (p.days > minDays && p !== best && p !== deficit && (!longest || p.days > longest.days)) longest = p;
    }
  }
  return { best, deficit, longest };
}
