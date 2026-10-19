import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { monthShort } from '@/shared/lib/dates';
import { formatMoney } from '@/shared/lib/money';
import { Card } from '@/shared/ui';
import type { TrendPoint } from '../types';

export function TrendChart({ points }: { points: TrendPoint[] }) {
  // Solo para dibujar alturas: los totales mostrados siguen siendo strings de la API.
  const data = points.map((p) => ({ label: monthShort(p.month), Ingresos: Number(p.income), Gastos: Number(p.expense), raw: p }));
  const summary = points.map((p) => `${monthShort(p.month)}: ingresos ${formatMoney(p.income)}, gastos ${formatMoney(p.expense)}`).join('; ');
  return (
    <Card className="flex flex-col gap-3.5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-base font-bold">Ingresos vs gastos</h2>
        <div className="flex gap-3 text-xs text-muted">
          <span className="flex items-center gap-1">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-income" />
            Ingresos
          </span>
          <span className="flex items-center gap-1">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-[#C2410C]" />
            Gastos
          </span>
        </div>
      </div>
      <div role="img" aria-label={`Ingresos contra gastos de los últimos meses. ${summary}`} className="h-[132px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }} barGap={3} barCategoryGap="22%">
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#55615B' }} />
            <Tooltip
              cursor={{ fill: 'rgba(15,94,85,0.06)' }}
              formatter={(v: number) => formatMoney(String(v))}
              contentStyle={{ borderRadius: 12, border: '1px solid #DDE3DE', fontSize: 12 }}
            />
            <Bar dataKey="Ingresos" fill="#1D4ED8" radius={[4, 4, 2, 2]} maxBarSize={14} isAnimationActive={false} />
            <Bar dataKey="Gastos" fill="#C2410C" radius={[4, 4, 2, 2]} maxBarSize={14} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
