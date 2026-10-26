import { Link } from 'react-router-dom';
import { Card, CardHeader, Money } from '@/shared/ui';
import { daysBetween, shortDate, todayISO, weekdayDate } from '@/shared/lib/dates';
import { useAuth } from '@/features/auth/AuthContext';
import { useLookups } from '@/features/transactions/lookups';
import { useUpcoming } from '@/features/recurring/hooks';
import type { UpcomingItem } from '@/features/recurring/types';
import type { NextPayday } from '../types';

/** Recurrentes que caen entre hoy y el próximo pago (incluido), con el sueldo marcado. */
export function BeforePayday({ nextPayday, fallback }: { nextPayday: NextPayday; fallback: UpcomingItem[] }) {
  const { user } = useAuth();
  const lookups = useLookups();
  const today = todayISO(user?.timezone);
  const days = Math.min(60, Math.max(7, daysBetween(today, nextPayday.date) + 1));
  const q = useUpcoming(days);
  const items = (q.data ?? fallback).filter((u) => u.date <= nextPayday.date);

  return (
    <Card className="flex flex-col gap-1.5">
      <CardHeader
        title="Antes de tu próximo pago"
        aside={
          <Link to="/metas?tab=recurrentes" className="font-semibold text-primary">
            Recurrentes
          </Link>
        }
      />
      {items.length === 0 ? (
        <p className="py-2 text-sm text-muted">Nada programado hasta tu pago del {weekdayDate(nextPayday.date)}.</p>
      ) : (
        <ul className="flex flex-col">
          {items.map((u, i) => (
            <li key={`${u.rule_id}-${u.date}-${i}`} className="flex items-center gap-3 py-2">
              <span aria-hidden="true" className="flex w-11 flex-col items-center rounded-[10px] bg-bg py-1">
                <span className="text-[11px] text-muted">{weekdayDate(u.date).split(' ')[0]}</span>
                <span className="text-[15px] font-bold">{Number(u.date.slice(8, 10))}</span>
              </span>
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-sm font-semibold">
                  {u.is_paycheck ? 'Sueldo' : u.note || lookups.categoryMap.get(u.category_id)?.name || 'Recurrente'}
                </span>
                <span className="truncate text-xs text-muted">
                  {u.is_paycheck ? 'Tu próximo pago' : lookups.categoryMap.get(u.category_id)?.name ?? shortDate(u.date)}
                </span>
              </span>
              <Money value={u.amount} type={u.type} className="text-sm font-bold" />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
