import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { amountToDigits, parseUserAmount } from '@/shared/lib/money';
import { positiveAmount } from '@/shared/lib/schemas';
import { Button, ConfirmSheet, Field, FormError, Input, Select, Sheet, errorMessage } from '@/shared/ui';
import type { Category } from '../../categories/types';
import { useCreateBudget, useDeleteBudget, useUpdateBudget } from '../hooks';
import type { BudgetStatus } from '../types';

const schema = z.object({
  category_id: z.string().min(1, 'Elige una categoría'),
  amount_limit: positiveAmount('Ingresa un límite mayor a 0'),
  threshold: z.string(),
});
type Values = z.infer<typeof schema>;

const THRESHOLDS = [50, 60, 70, 75, 80, 85, 90, 95];

export function BudgetFormSheet({
  open,
  onOpenChange,
  month,
  budget,
  categories,
  usedCategoryIds,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  month: string;
  budget: BudgetStatus | null;
  categories: Category[];
  usedCategoryIds: Set<string>;
}) {
  const create = useCreateBudget();
  const update = useUpdateBudget();
  const del = useDeleteBudget();
  const [confirm, setConfirm] = useState(false);
  const mutation = budget ? update : create;

  const available = categories.filter((c) => c.kind === 'expense' && (!usedCategoryIds.has(c.id) || c.id === budget?.category_id));

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { category_id: '', amount_limit: '', threshold: '80' } });

  useEffect(() => {
    if (!open) return;
    create.reset();
    update.reset();
    del.reset();
    setConfirm(false);
    reset({
      category_id: budget?.category_id ?? '',
      amount_limit: budget ? amountToDigits(budget.amount_limit) : '',
      threshold: String(Math.round(Number(budget?.alert_threshold ?? 0.8) * 100)),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, budget, reset]);

  const onSubmit = handleSubmit((v) => {
    const limit = parseUserAmount(v.amount_limit)!;
    const alert_threshold = Number(v.threshold) / 100;
    const done = { onSuccess: () => onOpenChange(false) };
    if (budget) update.mutate({ id: budget.id, amount_limit: limit, alert_threshold }, done);
    else create.mutate({ category_id: v.category_id, month, amount_limit: limit, alert_threshold }, done);
  });

  return (
    <>
      <Sheet open={open && !confirm} onOpenChange={onOpenChange} title={budget ? 'Editar presupuesto' : 'Nuevo presupuesto'}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <FormError message={mutation.isError ? errorMessage(mutation.error) : null} />
          <Field label="Categoría" error={errors.category_id?.message}>
            {(p) => (
              <Select {...p} disabled={!!budget} {...register('category_id')}>
                <option value="">Selecciona…</option>
                {available.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {!budget && available.length === 0 && (
            <p className="text-sm text-muted">Ya tienes presupuesto para todas tus categorías de gasto este mes.</p>
          )}
          <Field label="Límite mensual (COP)" error={errors.amount_limit?.message}>
            {(p) => <Input {...p} inputMode="decimal" placeholder="600000" autoComplete="off" {...register('amount_limit')} />}
          </Field>
          <Field label="Avisarme al llegar a" hint="Te mostraremos una alerta cuando el gasto alcance este porcentaje.">
            {(p) => (
              <Select {...p} {...register('threshold')}>
                {THRESHOLDS.map((t) => (
                  <option key={t} value={t}>
                    {t} %
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Button type="submit" size="lg" block loading={mutation.isPending}>
            Guardar
          </Button>
          {budget && (
            <Button variant="secondary" block className="text-expense" onClick={() => setConfirm(true)}>
              Eliminar presupuesto
            </Button>
          )}
        </form>
      </Sheet>
      <ConfirmSheet
        open={open && confirm}
        onOpenChange={(o) => !o && setConfirm(false)}
        title="¿Eliminar presupuesto?"
        message="Los movimientos de esta categoría no se borran; solo se quita el límite del mes."
        loading={del.isPending}
        error={del.isError ? errorMessage(del.error) : null}
        onConfirm={() => budget && del.mutate(budget.id, { onSuccess: () => onOpenChange(false) })}
      />
    </>
  );
}
