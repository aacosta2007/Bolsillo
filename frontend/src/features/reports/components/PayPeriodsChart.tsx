import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { shortDate } from '@/shared/lib/dates';
import { formatMoney } from '@/shared/lib/money';
import { Card } from '@/shared/ui';
import type { PayPeriod } from '../types';

/** Recibido vs gastado de las últimas quincenas, de la más antigua a la más reciente. */
export function PayPeriodsChart({ periods }: { periods: PayPeriod[] }) {
  const chrono = [...periods].reverse();
  // Solo para alturas: los montos mostrados salen de los strings de la API.
  const data = chrono.map((p) => ({ label: shortDate(p.start), Recibido: Number(p.income), Gastado: Number(p.expense) }));
  const summary = chrono
    .map((p) => `${shortDate(p.start)}: recibido ${formatMoney(p.income)}, gastado ${formatMoney(p.expense)}`)
    .join('; ');
  return (
    <Card className="flex flex-col gap-3.5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-base font-bold">Últimas {periods.length} quincenas</h2>
        <div className="flex gap-2.5 text-xs text-muted">
          <span className="flex items-center gap-1">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-[#2563EB]" />
            Recibido
          </span>
          <span className="flex items-center gap-1">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-[#C2410C]" />
            Gastado
          </span>
        </div>
      </div>
      <div role="img" aria-label={`Recibido contra gastado por quincena. ${summary}. El detalle está en la lista de abajo.`} className="h-[150px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }} barGap={3} barCategoryGap="20%">
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#55615B' }} interval={0} />
            <Tooltip
              cursor={{ fill: 'rgba(15,94,85,0.06)' }}
              formatter={(v: number) => formatMoney(String(v))}
              contentStyle={{ borderRadius: 12, border: '1px solid #DDE3DE', fontSize: 12 }}
            />
            <Bar dataKey="Recibido" fill="#2563EB" radius={[4, 4, 2, 2]} maxBarSize={12} isAnimationActive={false} />
            <Bar dataKey="Gastado" fill="#C2410C" radius={[4, 4, 2, 2]} maxBarSize={12} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
