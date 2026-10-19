import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Card, CardHeader, EmptyState, ErrorState, IconBadge, ListSkeleton, Segmented } from '@/shared/ui';
import { useCategories } from '../hooks';
import type { Category, CategoryKind } from '../types';
import { CategoryFormSheet } from './CategoryFormSheet';

export function CategoriesSection() {
  const q = useCategories();
  const [kind, setKind] = useState<CategoryKind>('expense');
  const [editing, setEditing] = useState<Category | null>(null);
  const [open, setOpen] = useState(false);
  const list = (q.data ?? []).filter((c) => c.kind === kind);

  return (
    <Card className="flex flex-col gap-2">
      <CardHeader
        title="Categorías"
        aside={
          <button
            type="button"
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
            className="flex min-h-[44px] items-center gap-1 font-semibold text-primary"
          >
            <Plus size={16} aria-hidden="true" />
            Nueva
          </button>
        }
      />
      <Segmented
        label="Tipo de categoría"
        value={kind}
        onChange={setKind}
        options={[
          { value: 'expense', label: 'Gastos' },
          { value: 'income', label: 'Ingresos' },
        ]}
      />
      {q.isLoading && <ListSkeleton rows={4} />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.isSuccess && list.length === 0 && <EmptyState title="Sin categorías" message="Crea una para clasificar tus movimientos." />}
      <ul className="grid grid-cols-1 divide-y divide-line-soft">
        {list.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => {
                setEditing(c);
                setOpen(true);
              }}
              aria-label={`Editar categoría ${c.name}`}
              className="flex min-h-[52px] w-full items-center gap-3 py-2 text-left"
            >
              <IconBadge icon={c.icon} color={c.color} size={36} rounded={10} />
              <span className="flex-1 truncate text-sm font-semibold">{c.name}</span>
            </button>
          </li>
        ))}
      </ul>
      <CategoryFormSheet open={open} onOpenChange={setOpen} category={editing} defaultKind={kind} />
    </Card>
  );
}
