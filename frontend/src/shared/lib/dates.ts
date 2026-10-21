export const DEFAULT_TZ = 'America/Bogota';

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MONTHS_SHORT = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const DOW_SHORT = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];

const pad = (n: number) => String(n).padStart(2, '0');

/** Fecha de hoy "YYYY-MM-DD" en la zona horaria dada. */
export function todayISO(tz: string = DEFAULT_TZ, now: Date = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
    return parts;
  } catch {
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  }
}

export function currentMonth(tz: string = DEFAULT_TZ, now: Date = new Date()): string {
  return todayISO(tz, now).slice(0, 7);
}

function parseISO(iso: string): { y: number; m: number; d: number } {
  const [y = 1970, m = 1, d = 1] = iso.slice(0, 10).split('-').map(Number);
  return { y, m, d };
}

export function monthStart(month: string): string {
  return `${month}-01`;
}

export function monthEnd(month: string): string {
  const [y = 1970, m = 1] = month.split('-').map(Number);
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return `${month}-${pad(last)}`;
}

export function shiftMonth(month: string, delta: number): string {
  const [y = 1970, m = 1] = month.split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}`;
}

/** "Octubre 2026" */
export function monthLabel(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const name = MONTHS[(m ?? 1) - 1] ?? '';
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} ${y}`;
}

export function monthName(month: string): string {
  const m = Number(month.split('-')[1]);
  return MONTHS[m - 1] ?? '';
}

/** "Oct" para gráficas */
export function monthShort(month: string): string {
  const m = Number(month.split('-')[1]);
  const s = MONTHS_SHORT[m - 1] ?? '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** "18 oct" */
export function shortDate(iso: string): string {
  const { m, d } = parseISO(iso);
  return `${d} ${MONTHS_SHORT[m - 1]}`;
}

/** "sáb 18 oct", con prefijo "Hoy · " / "Ayer · " */
export function dayLabel(iso: string, today: string): string {
  const { y, m, d } = parseISO(iso);
  const dow = DOW_SHORT[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  const base = `${dow} ${d} ${MONTHS_SHORT[m - 1]}`;
  if (iso === today) return `Hoy · ${base}`;
  if (iso === addDays(today, -1)) return `Ayer · ${base}`;
  return base.charAt(0).toUpperCase() + base.slice(1);
}

/** "jue 15 oct" (minúsculas, sin prefijo). */
export function weekdayDate(iso: string): string {
  const { y, m, d } = parseISO(iso);
  return `${DOW_SHORT[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]} ${d} ${MONTHS_SHORT[m - 1]}`;
}

export function addDays(iso: string, n: number): string {
  const { y, m, d } = parseISO(iso);
  const dt = new Date(Date.UTC(y, m - 1, d + n));
  return `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`;
}

/** Días que faltan para terminar el mes de `today` (incluye hoy). */
export function daysLeftInMonth(today: string): number {
  const { d } = parseISO(today);
  const end = parseISO(monthEnd(today.slice(0, 7))).d;
  return end - d + 1;
}

export function formatDateLong(iso: string): string {
  const { y, m, d } = parseISO(iso);
  return `${d} de ${MONTHS[m - 1]} de ${y}`;
}

export const FREQ_LABEL: Record<string, string> = {
  daily: 'Diario',
  weekly: 'Semanal',
  monthly: 'Mensual',
  yearly: 'Anual',
};
