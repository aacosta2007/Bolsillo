import { useState } from 'react';
import { Plus } from 'lucide-react';
import { monthName } from '@/shared/lib/dates';
import { formatMoney } from '@/shared/lib/money';
import { Button, EmptyState, ErrorState, ListSkeleton } from '@/shared/ui';
import { useGoals } from '../hooks';
import type { Goal } from '../types';
import { GoalRing } from './GoalRing';
import { GoalFormSheet } from './GoalFormSheet';
import { ContributionSheet } from './ContributionSheet';

export function goalHint(g: Goal): string {
  if (g.completed) return '¡Meta cumplida!';
  const until = g.target_date ? `${monthName(g.target_date.slice(0, 7)).slice(0, 3)} ${g.target_date.slice(0, 4)}` : null;
  if (g.monthly_needed && until) return `${formatMoney(g.monthly_needed)} al mes hasta ${until}`;
  if (until) return `Fecha límite: ${until}`;
  return 'Sin fecha límite';
}

export function GoalsTab() {
  const goals = useGoals();
  const [editing, setEditing] = useState<Goal | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [contributing, setContributing] = useState<Goal | null>(null);

  const openNew = () => {
    setEditing(null);
    setFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-3">
      {goals.isLoading && <ListSkeleton rows={3} />}
      {goals.isError && <ErrorState error={goals.error} onRetry={() => goals.refetch()} />}
      {goals.isSuccess && goals.data.length === 0 && (
        <EmptyState title="Aún no tienes metas" message="Crea una meta de ahorro y ve cómo avanzas con cada aporte." />
      )}

      {goals.data?.map((g) => {
        const color = g.color || '#0F5E55';
        return (
          <div key={g.id} className="flex items-center gap-3.5 rounded-card bg-surface p-4">
            <GoalRing percent={g.percent} color={color} label={`${g.name}: ${Math.round(g.percent)} por ciento`} />
            <button
              type="button"
              onClick={() => {
                setEditing(g);
                setFormOpen(true);
              }}
              aria-label={`Editar meta ${g.name}`}
              className="flex min-h-[44px] min-w-0 flex-1 flex-col gap-[3px] text-left"
            >
              <span className="truncate text-[15px] font-bold">{g.name}</span>
              <span className="tnum text-[13px] text-[#3D4843]">
                {formatMoney(g.saved)} de {formatMoney(g.target_amount)}
              </span>
              <span className="text-xs text-muted">{goalHint(g)}</span>
            </button>
            <button
              type="button"
              aria-label={`Aportar a ${g.name}`}
              onClick={() => setContributing(g)}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-ctl2 border border-line bg-surface text-primary hover:bg-primary-tint"
            >
              <Plus size={18} strokeWidth={2.4} aria-hidden="true" />
            </button>
          </div>
        );
      })}

      <Button size="lg" block onClick={openNew}>
        Nueva meta de ahorro
      </Button>

      <GoalFormSheet open={formOpen} onOpenChange={setFormOpen} goal={editing} />
      <ContributionSheet goal={contributing} onClose={() => setContributing(null)} />
    </div>
  );
}
