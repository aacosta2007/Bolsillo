import { CalendarRange } from 'lucide-react';
import { EmptyState, ErrorState, ListSkeleton, Skeleton } from '@/shared/ui';
import { usePayPeriods } from '../hooks';
import { PayPeriodsChart } from './PayPeriodsChart';
import { PayPeriodsList } from './PayPeriodsList';
import { PayPeriodsSummary } from './PayPeriodsSummary';

export function PayPeriodsTab() {
  const q = usePayPeriods(6);
  return (
    <div className="flex flex-col gap-4">
      {q.isLoading && (
        <div role="status" aria-label="Cargando quincenas" className="flex flex-col gap-4">
          <Skeleton className="h-[220px] rounded-card" />
          <ListSkeleton rows={4} />
        </div>
      )}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.isSuccess && q.data.length === 0 && (
        <EmptyState
          title="Aún no hay quincenas"
          message="Registra movimientos y marca tu sueldo como recurrente para medir de pago a pago."
          icon={<CalendarRange size={22} aria-hidden="true" />}
        />
      )}
      {q.isSuccess && q.data.length > 0 && (
        <>
          <PayPeriodsChart periods={q.data} />
          <PayPeriodsList periods={q.data} />
          <PayPeriodsSummary periods={q.data} />
        </>
      )}
    </div>
  );
}
