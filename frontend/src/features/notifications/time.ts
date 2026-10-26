import { shortDate, todayISO, addDays } from '@/shared/lib/dates';

/** Fecha local "YYYY-MM-DD" de un instante en la zona dada. */
const localDate = (d: Date, tz: string) => todayISO(tz, d);

/** "ahora", "hace 5 min", "hace 2 h", "ayer", "15 oct" (con año si no es el actual). */
export function relativeTime(iso: string, tz: string, now: Date = new Date()): string {
  const then = new Date(iso);
  const diffMin = Math.floor((now.getTime() - then.getTime()) / 60_000);
  if (Number.isNaN(diffMin)) return '';
  if (diffMin < 1) return 'ahora';
  const today = localDate(now, tz);
  const day = localDate(then, tz);
  if (day === today) {
    if (diffMin < 60) return `hace ${diffMin} min`;
    return `hace ${Math.floor(diffMin / 60)} h`;
  }
  if (day === addDays(today, -1)) return 'ayer';
  const label = shortDate(day);
  return day.slice(0, 4) === today.slice(0, 4) ? label : `${label} ${day.slice(0, 4)}`;
}
