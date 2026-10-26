import { CalendarDays } from 'lucide-react';
import { EmptyState } from '@/shared/ui';

/** Placeholder: el reporte mensual lo implementa otro PR. */
export function MonthTab() {
  return (
    <EmptyState
      title="El reporte mensual llega pronto"
      message="Mientras tanto, mira cómo te fue de pago a pago en la pestaña Quincenas."
      icon={<CalendarDays size={22} aria-hidden="true" />}
    />
  );
}
