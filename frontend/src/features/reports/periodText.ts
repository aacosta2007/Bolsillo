import { formatMoney, formatMoneyWhole, toCents } from '@/shared/lib/money';
import type { PayPeriod } from './types';

/** Titular del neto de un periodo: nunca "Disponible − $ X"; el negativo se dice con palabras. */
export function netHeadline(p: PayPeriod): string {
  if (toCents(p.net) < 0n) return `Gastaste ${formatMoney(p.net.replace('-', ''))} más de lo que recibiste`;
  return p.in_progress ? `Disponible ${formatMoney(p.net)}` : `Sobraron ${formatMoney(p.net)}`;
}

/** "$ 60.140 por día" o "Sin gastos" cuando no se gastó nada. */
export function perDayText(p: PayPeriod, suffix = ' por día'): string | null {
  if (toCents(p.expense) === 0n) return 'Sin gastos';
  return p.spent_per_day ? `${formatMoneyWhole(p.spent_per_day)}${suffix}` : null;
}

/** "Sueldo $ X · Extra $ Y" (o solo "Recibido $ X" si no hay desglose útil: calendario o sin extra). */
export function receivedText(p: PayPeriod): string {
  if (p.source === 'calendar' || toCents(p.extra_income) === 0n) return `Recibido ${formatMoney(p.income)}`;
  return `Sueldo ${formatMoney(p.salary_income)} · Extra ${formatMoney(p.extra_income)}`;
}
