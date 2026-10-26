import { currentMonth, DEFAULT_TZ, shiftMonth, todayISO } from '@/shared/lib/dates';
import { formatPercent } from '@/shared/lib/money';

const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

/** Mes por defecto: el anterior si hoy es día 1–5, si no el mes en curso. */
export function defaultReportMonth(tz: string = DEFAULT_TZ, now: Date = new Date()): string {
  const today = todayISO(tz, now);
  const day = Number(today.slice(8, 10));
  const cur = today.slice(0, 7);
  return day <= 5 ? shiftMonth(cur, -1) : cur;
}

/** Valida el parámetro `mes` de la URL: formato correcto y no futuro; si no, el mes por defecto. */
export function resolveReportMonth(param: string | null, tz: string = DEFAULT_TZ, now: Date = new Date()): string {
  if (param && MONTH_RE.test(param) && param <= currentMonth(tz, now)) return param;
  return defaultReportMonth(tz, now);
}

export type ChangeKind = 'expense' | 'income';
export type ChangeTone = 'good' | 'bad' | 'neutral';

export interface Change {
  /** Texto visible, p. ej. "▲ 18 %". */
  text: string;
  /** Texto para lectores de pantalla, p. ej. "subió 18 %". */
  sr: string;
  tone: ChangeTone;
}

export const TONE_CLASS: Record<ChangeTone, string> = {
  good: 'text-primary',
  bad: 'text-expense',
  neutral: 'text-muted',
};

/**
 * Variación porcentual. En gastos subir es malo; en ingresos/ahorro subir es bueno.
 * `null` sin `isNew` → sin comparación (devuelve null).
 */
export function describeChange(pct: number | null | undefined, kind: ChangeKind, isNew = false): Change | null {
  if (pct === null || pct === undefined) {
    if (!isNew) return null;
    return { text: 'nuevo', sr: 'nuevo este mes', tone: kind === 'income' ? 'good' : 'neutral' };
  }
  const abs = formatPercent(Math.abs(pct), 1);
  if (Math.abs(pct) < 0.05) return { text: '= 0 %', sr: 'sin cambios', tone: 'neutral' };
  const up = pct > 0;
  const good = kind === 'income' ? up : !up;
  return { text: `${up ? '▲' : '▼'} ${abs}`, sr: `${up ? 'subió' : 'bajó'} ${abs}`, tone: good ? 'good' : 'bad' };
}

/** Variación de la tasa de ahorro en puntos porcentuales (subir es bueno). */
export function describePoints(rate: number | null | undefined, prev: number | null | undefined): Change | null {
  if (rate === null || rate === undefined || prev === null || prev === undefined) return null;
  const diff = rate - prev;
  const abs = Math.abs(diff).toFixed(1).replace(/\.0$/, '').replace('.', ',');
  if (Math.abs(diff) < 0.05) return { text: '= 0 pts', sr: 'sin cambios', tone: 'neutral' };
  const up = diff > 0;
  return { text: `${up ? '▲' : '▼'} ${abs} pts`, sr: `${up ? 'subió' : 'bajó'} ${abs} puntos`, tone: up ? 'good' : 'bad' };
}
