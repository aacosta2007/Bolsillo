import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { todayISO } from '@/shared/lib/dates';
import { amountToDigits, parseUserAmount } from '@/shared/lib/money';
import { positiveAmount } from '@/shared/lib/schemas';
import { Button, ConfirmSheet, Field, FormError, Input, Segmented, Select, Sheet, errorMessage } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { useAccounts } from '../../accounts/hooks';
import { useCategories } from '../../categories/hooks';
import { useCreateRecurring, useDeleteRecurring, useUpdateRecurring } from '../hooks';
import type { Frequency, RecurringRule } from '../types';

const schema = z.object({
  amount: positiveAmount(),
  account_id: z.string().min(1, 'Elige una cuenta'),
  category_id: z.string().min(1, 'Elige una categoría'),
  note: z.string().max(255),
  frequency: z.enum(['daily', 'weekly', 'monthly', 'yearly']),
  interval: z.string().regex(/^[1-9]\d{0,2}$/, 'Debe ser un número mayor a 0'),
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Elige una fecha'),
  end_date: z.string(),
  active: z.boolean(),
});
type Values = z.infer<typeof schema>;

const FREQ: Array<{ value: Frequency; label: string }> = [
  { value: 'daily', label: 'Diaria' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'monthly', label: 'Mensual' },
  { value: 'yearly', label: 'Anual' },
];

export function RecurringFormSheet({ open, onOpenChange, rule }: { open: boolean; onOpenChange: (o: boolean) => void; rule: RecurringRule | null }) {
  const { user } = useAuth();
  const today = todayISO(user?.timezone);
  const accounts = useAccounts(false);
  const categories = useCategories();
  const create = useCreateRecurring();
  const update = useUpdateRecurring();
  const del = useDeleteRecurring();
  const [type, setType] = useState<'expense' | 'income'>('expense');
  const [confirm, setConfirm] = useState(false);
  const mutation = rule ? update : create;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { amount: '', account_id: '', category_id: '', note: '', frequency: 'monthly', interval: '1', start_date: today, end_date: '', active: true },
  });

  useEffect(() => {
    if (!open) return;
    create.reset();
    update.reset();
    del.reset();
    setConfirm(false);
    setType(rule?.type ?? 'expense');
    reset({
      amount: rule ? amountToDigits(rule.amount) : '',
      account_id: rule?.account_id ?? accounts.data?.[0]?.id ?? '',
      category_id: rule?.category_id ?? '',
      note: rule?.note ?? '',
      frequency: rule?.frequency ?? 'monthly',
      interval: String(rule?.interval ?? 1),
      start_date: rule?.start_date ?? today,
      end_date: rule?.end_date ?? '',
      active: rule?.active ?? true,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, rule, reset, today, accounts.data]);

  const cats = (categories.data ?? []).filter((c) => c.kind === type);

  const onSubmit = handleSubmit((v) => {
    const body = {
      type,
      amount: parseUserAmount(v.amount)!,
      account_id: v.account_id,
      category_id: v.category_id,
      note: v.note.trim() || null,
      frequency: v.frequency,
      interval: Number(v.interval),
      start_date: v.start_date,
      end_date: v.end_date || null,
      active: v.active,
    };
    const done = { onSuccess: () => onOpenChange(false) };
    if (rule) update.mutate({ id: rule.id, ...body }, done);
    else create.mutate(body, done);
  });

  return (
    <>
      <Sheet open={open && !confirm} onOpenChange={onOpenChange} title={rule ? 'Editar recurrente' : 'Nuevo recurrente'}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <FormError message={mutation.isError ? errorMessage(mutation.error) : null} />
          <Segmented
            label="Tipo"
            value={type}
            onChange={(t) => {
              setType(t);
              setValue('category_id', '');
            }}
            options={[
              { value: 'expense', label: 'Gasto' },
              { value: 'income', label: 'Ingreso' },
            ]}
          />
          <Field label="Nota" error={errors.note?.message}>
            {(p) => <Input {...p} placeholder="Ej. Netflix, Arriendo" maxLength={255} {...register('note')} />}
          </Field>
          <Field label="Monto (COP)" error={errors.amount?.message}>
            {(p) => <Input {...p} inputMode="decimal" placeholder="39900" autoComplete="off" {...register('amount')} />}
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Cuenta" error={errors.account_id?.message}>
              {(p) => (
                <Select {...p} {...register('account_id')}>
                  <option value="">Selecciona…</option>
                  {(accounts.data ?? []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Categoría" error={errors.category_id?.message}>
              {(p) => (
                <Select {...p} {...register('category_id')}>
                  <option value="">Selecciona…</option>
                  {cats.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Frecuencia">
              {(p) => (
                <Select {...p} {...register('frequency')}>
                  {FREQ.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Cada cuántos" error={errors.interval?.message}>
              {(p) => <Input {...p} inputMode="numeric" {...register('interval')} />}
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Inicia" error={errors.start_date?.message}>
              {(p) => <Input {...p} type="date" {...register('start_date')} />}
            </Field>
            <Field label="Termina (opcional)">{(p) => <Input {...p} type="date" {...register('end_date')} />}</Field>
          </div>
          {rule && (
            <label className="flex min-h-[44px] items-center gap-3 text-sm font-semibold">
              <input type="checkbox" className="h-5 w-5 accent-primary" {...register('active')} />
              Activo
            </label>
          )}
          <Button type="submit" size="lg" block loading={mutation.isPending}>
            Guardar
          </Button>
          {rule && (
            <Button variant="secondary" block className="text-expense" onClick={() => setConfirm(true)}>
              Eliminar recurrente
            </Button>
          )}
        </form>
      </Sheet>
      <ConfirmSheet
        open={open && confirm}
        onOpenChange={(o) => !o && setConfirm(false)}
        title="¿Eliminar recurrente?"
        message="Los movimientos ya generados se conservan; no se crearán más."
        loading={del.isPending}
        error={del.isError ? errorMessage(del.error) : null}
        onConfirm={() => rule && del.mutate(rule.id, { onSuccess: () => onOpenChange(false) })}
      />
    </>
  );
}
