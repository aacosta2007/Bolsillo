import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Trash2 } from 'lucide-react';
import { shortDate, todayISO } from '@/shared/lib/dates';
import { parseUserAmount } from '@/shared/lib/money';
import { positiveAmount } from '@/shared/lib/schemas';
import { Button, Field, FormError, Input, Money, Segmented, Sheet, errorMessage } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { useAddContribution, useContributions, useRemoveContribution } from '../hooks';
import type { Goal } from '../types';

const schema = z.object({
  amount: positiveAmount(),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Elige una fecha'),
  note: z.string().max(255),
});
type Values = z.infer<typeof schema>;

export function ContributionSheet({ goal, onClose }: { goal: Goal | null; onClose: () => void }) {
  const { user } = useAuth();
  const today = todayISO(user?.timezone);
  const add = useAddContribution();
  const remove = useRemoveContribution();
  const history = useContributions(goal?.id);
  const [mode, setMode] = useState<'add' | 'withdraw'>('add');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { amount: '', date: today, note: '' } });

  useEffect(() => {
    if (goal) {
      reset({ amount: '', date: today, note: '' });
      setMode('add');
      add.reset();
      remove.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goal?.id, reset, today]);

  if (!goal) return null;

  const onSubmit = handleSubmit((v) => {
    const abs = parseUserAmount(v.amount)!;
    add.mutate(
      { id: goal.id, amount: mode === 'withdraw' ? `-${abs}` : abs, date: v.date, note: v.note.trim() || null },
      { onSuccess: () => reset({ amount: '', date: today, note: '' }) },
    );
  });

  const err = add.isError ? errorMessage(add.error) : remove.isError ? errorMessage(remove.error) : null;

  return (
    <Sheet open onOpenChange={(o) => !o && onClose()} title={goal.name} description="Registra aportes o retiros de esta meta.">
      <div className="flex flex-col gap-4">
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-3">
          <FormError message={err} />
          <Segmented
            label="Tipo de aporte"
            value={mode}
            onChange={setMode}
            options={[
              { value: 'add', label: 'Aportar' },
              { value: 'withdraw', label: 'Retirar' },
            ]}
          />
          <Field label="Monto (COP)" error={errors.amount?.message}>
            {(p) => <Input {...p} inputMode="decimal" placeholder="250000" autoComplete="off" {...register('amount')} />}
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Fecha" error={errors.date?.message}>
              {(p) => <Input {...p} type="date" {...register('date')} />}
            </Field>
            <Field label="Nota (opcional)">{(p) => <Input {...p} maxLength={255} {...register('note')} />}</Field>
          </div>
          <Button type="submit" size="lg" block loading={add.isPending}>
            {mode === 'add' ? 'Guardar aporte' : 'Guardar retiro'}
          </Button>
        </form>

        <section aria-label="Historial de aportes" className="flex flex-col">
          <h3 className="pb-1 text-sm font-bold">Historial</h3>
          {history.isLoading && <p className="py-2 text-sm text-muted">Cargando…</p>}
          {history.isError && <p className="py-2 text-sm text-expense">{errorMessage(history.error)}</p>}
          {history.data?.length === 0 && <p className="py-2 text-sm text-muted">Aún no hay aportes.</p>}
          <ul className="divide-y divide-line-soft">
            {history.data?.map((c) => (
              <li key={c.id} className="flex min-h-[48px] items-center gap-3 py-1.5 text-sm">
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-semibold">{shortDate(c.date)}</span>
                  {c.note && <span className="truncate text-xs text-muted">{c.note}</span>}
                </span>
                <Money value={c.amount.replace('-', '')} type={c.amount.startsWith('-') ? 'expense' : 'income'} className="font-bold" />
                <button
                  type="button"
                  aria-label={`Eliminar aporte del ${shortDate(c.date)}`}
                  onClick={() => remove.mutate({ id: goal.id, cid: c.id })}
                  className="flex h-11 w-11 items-center justify-center rounded-ctl text-muted hover:bg-bg"
                >
                  <Trash2 size={16} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </Sheet>
  );
}
