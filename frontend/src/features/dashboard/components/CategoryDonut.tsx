import { Cell, Pie, PieChart } from 'recharts';
import { formatPercent } from '@/shared/lib/money';
import { Card, CardHeader } from '@/shared/ui';
import type { CategoryTotal } from '../types';

const FALLBACK = ['#0F5E55', '#C2410C', '#2563EB', '#F2A65A', '#93C5BB', '#6D28D9', '#BE185D', '#0E7490', '#B7791F'];

export interface Slice {
  name: string;
  percent: number;
  color: string;
}

/** Top 5 categorías + "Otros" con el resto. */
export function toSlices(rows: CategoryTotal[]): Slice[] {
  const top = rows.slice(0, 5).map((r, i) => ({ name: r.name, percent: r.percent, color: r.color || FALLBACK[i % FALLBACK.length]! }));
  const rest = rows.slice(5);
  if (rest.length) top.push({ name: 'Otros', percent: rest.reduce((a, r) => a + r.percent, 0), color: '#93C5BB' });
  return top;
}

export function CategoryDonut({ rows }: { rows: CategoryTotal[] }) {
  const slices = toSlices(rows);
  const label = slices.map((s) => `${s.name} ${formatPercent(s.percent, 0)}`).join(', ');
  return (
    <Card className="flex flex-col gap-3.5">
      <CardHeader title="Gastos por categoría" aside="Este mes" />
      {slices.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">Aún no hay gastos en este periodo.</p>
      ) : (
        <div className="flex items-center gap-4">
          <div role="img" aria-label={`Gráfico de dona de gastos por categoría: ${label}`} className="shrink-0">
            <PieChart width={132} height={132}>
              <Pie
                data={slices}
                dataKey="percent"
                nameKey="name"
                innerRadius={40}
                outerRadius={64}
                paddingAngle={slices.length > 1 ? 2 : 0}
                stroke="none"
                isAnimationActive={false}
              >
                {slices.map((s) => (
                  <Cell key={s.name} fill={s.color} />
                ))}
              </Pie>
            </PieChart>
          </div>
          <ul className="flex flex-1 flex-col gap-2 text-[13px]">
            {slices.map((s) => (
              <li key={s.name} className="flex items-center gap-2">
                <span aria-hidden="true" className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: s.color }} />
                <span className="flex-1 truncate">{s.name}</span>
                <span className="tnum font-semibold">{formatPercent(s.percent, 0)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
