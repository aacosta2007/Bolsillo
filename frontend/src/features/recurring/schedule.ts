/**
 * Calendario de recurrentes (lógica pura, espejo del contrato del API):
 * - `monthly_days`: días 1–31 o `L` (último); un día inexistente se ajusta al último del mes
 *   y las fechas repetidas se deduplican.
 * - `weekend_adjust`: sábado/domingo → viernes anterior (fecha efectiva).
 * - El monto de `monthly_days` es por ocurrencia.
 */
import { addDays } from '@/shared/lib/dates';
import type { Frequency, WeekendAdjust } from './types';

export type DayValue = number | 'L';

/** Opción elegida en el selector "¿Cada cuánto?". */
export type ScheduleMode = 'q15L' | 'q1530' | 'monthly' | 'weekly' | 'custom' | 'more';

export const MAX_DAYS = 3;

const pad = (n: number) => String(n).padStart(2, '0');

function parts(iso: string): { y: number; m: number; d: number } {
  const [y = 1970, m = 1, d = 1] = iso.slice(0, 10).split('-').map(Number);
  return { y, m, d };
}

export function daysInMonth(y: number, m: number): number {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}

const toISO = (y: number, m: number, d: number) => `${y}-${pad(m)}-${pad(d)}`;

/** "15,L" → [15, 'L'] (ignora valores no válidos y repetidos). */
export function parseDays(spec: string | null | undefined): DayValue[] {
  if (!spec) return [];
  const out: DayValue[] = [];
  for (const raw of spec.split(',')) {
    const t = raw.trim().toUpperCase();
    const v: DayValue | null = t === 'L' ? 'L' : /^\d{1,2}$/.test(t) && Number(t) >= 1 && Number(t) <= 31 ? Number(t) : null;
    if (v !== null && !out.includes(v)) out.push(v);
  }
  return out;
}

/** Ordena números ascendente y deja L al final: [15, 'L', 5] → "5,15,L". */
export function formatDays(days: DayValue[]): string {
  const nums = days.filter((d): d is number => d !== 'L').sort((a, b) => a - b);
  return [...nums, ...(days.includes('L') ? ['L'] : [])].join(',');
}

/** Opción del selector que corresponde a una regla existente. */
export function modeFromRule(r: { frequency: Frequency; days_of_month: string | null }): ScheduleMode {
  switch (r.frequency) {
    case 'monthly_days': {
      const spec = formatDays(parseDays(r.days_of_month));
      return spec === '15,L' ? 'q15L' : spec === '15,30' ? 'q1530' : 'custom';
    }
    case 'monthly':
      return 'monthly';
    case 'weekly':
      return 'weekly';
    default:
      return 'more';
  }
}

/** frequency + days_of_month que se envían al API para una opción. `classic` aplica a la opción "más". */
export function scheduleFromMode(
  mode: ScheduleMode,
  custom: DayValue[],
  classic: Exclude<Frequency, 'monthly_days'>,
): { frequency: Frequency; days_of_month: string | null } {
  switch (mode) {
    case 'q15L':
      return { frequency: 'monthly_days', days_of_month: '15,L' };
    case 'q1530':
      return { frequency: 'monthly_days', days_of_month: '15,30' };
    case 'custom':
      return { frequency: 'monthly_days', days_of_month: formatDays(custom) };
    case 'monthly':
      return { frequency: 'monthly', days_of_month: null };
    case 'weekly':
      return { frequency: 'weekly', days_of_month: null };
    case 'more':
      return { frequency: classic, days_of_month: null };
  }
}

function resolveDay(d: DayValue, y: number, m: number): number {
  const last = daysInMonth(y, m);
  return d === 'L' ? last : Math.min(d, last);
}

/** Fechas nominales de un mes (ordenadas, sin repetir) para una lista de días. */
export function monthOccurrences(days: DayValue[], y: number, m: number): string[] {
  const set = new Set(days.map((d) => resolveDay(d, y, m)));
  return [...set].sort((a, b) => a - b).map((d) => toISO(y, m, d));
}

/** Sábado/domingo → viernes anterior. */
export function adjustWeekend(date: string): string {
  const { y, m, d } = parts(date);
  const dow = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  if (dow === 6) return addDays(date, -1);
  if (dow === 0) return addDays(date, -2);
  return date;
}

export interface ScheduleInput {
  frequency: Frequency;
  interval: number;
  days_of_month: string | null;
  weekend_adjust: WeekendAdjust;
  start_date: string;
  end_date?: string | null;
}

export interface Occurrence {
  /** Fecha nominal (sin ajuste). */
  nominal: string;
  /** Fecha efectiva (con ajuste de fin de semana si aplica). */
  date: string;
  adjusted: boolean;
}

function addMonthsClamped(startISO: string, months: number): string {
  const { y, m, d } = parts(startISO);
  const total = y * 12 + (m - 1) + months;
  const ny = Math.floor(total / 12);
  const nm = (total % 12) + 1;
  return toISO(ny, nm, Math.min(d, daysInMonth(ny, nm)));
}

function* nominalDates(s: ScheduleInput, from: string): Generator<string> {
  const step = Math.max(1, Math.floor(s.interval) || 1);
  if (s.frequency === 'monthly_days') {
    const days = parseDays(s.days_of_month);
    if (days.length === 0) return;
    let { y, m } = parts(from);
    for (let i = 0; i < 1200; i++) {
      for (const dt of monthOccurrences(days, y, m)) if (dt >= from) yield dt;
      m += 1;
      if (m > 12) {
        m = 1;
        y += 1;
      }
    }
    return;
  }
  for (let k = 0; k < 20000; k++) {
    let dt: string;
    switch (s.frequency) {
      case 'daily':
        dt = addDays(s.start_date, k * step);
        break;
      case 'weekly':
        dt = addDays(s.start_date, 7 * step * k);
        break;
      case 'monthly':
        dt = addMonthsClamped(s.start_date, k * step);
        break;
      default:
        dt = addMonthsClamped(s.start_date, 12 * k * step);
    }
    if (dt >= from) yield dt;
  }
}

/**
 * Próximas `count` ocurrencias con nominal >= `from` (por defecto `start_date`) y <= `end_date`.
 * Para `monthly_days` solo cuentan los días elegidos; para el resto, el patrón arranca en `start_date`.
 */
export function upcomingOccurrences(s: ScheduleInput, count = 4, from?: string): Occurrence[] {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s.start_date)) return [];
  const lower = from && from > s.start_date ? from : s.start_date;
  const out: Occurrence[] = [];
  for (const nominal of nominalDates(s, lower)) {
    if (s.end_date && nominal > s.end_date) break;
    const date = s.weekend_adjust === 'previous_business_day' ? adjustWeekend(nominal) : nominal;
    out.push({ nominal, date, adjusted: date !== nominal });
    if (out.length >= count) break;
  }
  return out;
}

function divRound(num: bigint, den: bigint): bigint {
  return (num * 2n + den) / (den * 2n);
}

/** Equivalente mensual en centavos (misma fórmula que el API, redondeo half-up a centavos). */
export function monthlyEquivalentCents(amountCents: bigint, frequency: Frequency, interval: number, daysCount = 1): bigint {
  const n = BigInt(Math.max(1, Math.floor(interval) || 1));
  switch (frequency) {
    case 'monthly_days':
      return amountCents * BigInt(Math.max(1, daysCount));
    case 'monthly':
      return divRound(amountCents, n);
    case 'weekly':
      return divRound(amountCents * 52n, 12n * n);
    case 'daily':
      return divRound(amountCents * 365n, 12n * n);
    case 'yearly':
      return divRound(amountCents, 12n * n);
  }
}

/** Descripción corta en español de la frecuencia de una regla. */
export function describeFrequency(r: {
  frequency: Frequency;
  interval: number;
  days_of_month: string | null;
  start_date: string;
}): string {
  const dayOfStart = Number(r.start_date.slice(8, 10));
  switch (r.frequency) {
    case 'monthly_days': {
      const days = parseDays(r.days_of_month);
      const spec = formatDays(days);
      if (spec === '15,L') return 'Quincenal · 15 y último día';
      if (spec === '15,30') return 'Quincenal · 15 y 30';
      if (days.length === 1) return days[0] === 'L' ? 'Mensual · último día' : `Mensual · día ${days[0]}`;
      return `Días ${spec.split(',').map((d) => (d === 'L' ? 'último' : d)).join(', ')}`;
    }
    case 'monthly':
      return r.interval > 1 ? `Cada ${r.interval} meses · día ${dayOfStart}` : `Mensual · día ${dayOfStart}`;
    case 'weekly':
      return r.interval > 1 ? `Cada ${r.interval} semanas` : 'Semanal';
    case 'daily':
      return r.interval > 1 ? `Cada ${r.interval} días` : 'Diaria';
    case 'yearly':
      return r.interval > 1 ? `Cada ${r.interval} años · día ${dayOfStart}` : `Anual · día ${dayOfStart}`;
  }
}
