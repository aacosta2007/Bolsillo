import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { amountToDigits, parseUserAmount } from '@/shared/lib/money';
import { positiveAmount } from '@/shared/lib/schemas';
import { Button, ColorPicker, ConfirmSheet, Field, FormError, IconPicker, Input, Select, Sheet, errorMessage } from '@/shared/ui';
import { useAccounts } from '../../accounts/hooks';
import { useCreateGoal, useDeleteGoal, useUpdateGoal } from '../hooks';
import type { Goal } from '../types';

const schema = z.object({
  name: z.string().trim().min(1, 'Ponle un nombre a tu meta').max(100),
  target_amount: positiveAmount('Ingresa una meta mayor a 0'),
  target_date: z.string(),
  account_id: z.string(),
});
type Values = z.infer<typeof schema>;

export function GoalFormSheet({ open, onOpenChange, goal }: { open: boolean; onOpenChange: (o: boolean) => void; goal: Goal | null }) {
  const accounts = useAccounts(false);
  const create = useCreateGoal();
  const update = useUpdateGoal();
  const del = useDeleteGoal();
  const [color, setColor] = useState('#0F5E55');
  const [icon, setIcon] = useState('target');
  const [confirm, setConfirm] = useState(false);
  const mutation = goal ? update : create;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { name: '', target_amount: '', target_date: '', account_id: '' } });

  useEffect(() => {
    if (!open) return;
    create.reset();
    update.reset();
    del.reset();
    setConfirm(false);
    setColor(goal?.color ?? '#0F5E55');
    setIcon(goal?.icon ?? 'target');
    reset({
      name: goal?.name ?? '',
      target_amount: goal ? amountToDigits(goal.target_amount) : '',
      target_date: goal?.target_date ?? '',
      account_id: goal?.account_id ?? '',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, goal, reset]);

  const onSubmit = handleSubmit((v) => {
    const body = {
      name: v.name.trim(),
      target_amount: parseUserAmount(v.target_amount)!,
      target_date: v.target_date || null,
      account_id: v.account_id || null,
      color,
      icon,
    };
    const done = { onSuccess: () => onOpenChange(false) };
    if (goal) update.mutate({ id: goal.id, ...body }, done);
    else create.mutate(body, done);
  });

  return (
    <>
      <Sheet open={open && !confirm} onOpenChange={onOpenChange} title={goal ? 'Editar meta' : 'Nueva meta de ahorro'}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <FormError message={mutation.isError ? errorMessage(mutation.error) : null} />
          <Field label="Nombre" error={errors.name?.message}>
            {(p) => <Input {...p} placeholder="Ej. Viaje a Cartagena" maxLength={100} {...register('name')} />}
          </Field>
          <Field label="Monto objetivo (COP)" error={errors.target_amount?.message}>
            {(p) => <Input {...p} inputMode="decimal" placeholder="3000000" autoComplete="off" {...register('target_amount')} />}
          </Field>
          <Field label="Fecha límite (opcional)">{(p) => <Input {...p} type="date" {...register('target_date')} />}</Field>
          <Field label="Cuenta vinculada (opcional)">
            {(p) => (
              <Select {...p} {...register('account_id')}>
                <option value="">Sin cuenta</option>
                {(accounts.data ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <ColorPicker value={color} onChange={setColor} />
          <IconPicker value={icon} onChange={setIcon} color={color} />
          <Button type="submit" size="lg" block loading={mutation.isPending}>
            Guardar meta
          </Button>
          {goal && (
            <Button variant="secondary" block className="text-expense" onClick={() => setConfirm(true)}>
              Eliminar meta
            </Button>
          )}
        </form>
      </Sheet>
      <ConfirmSheet
        open={open && confirm}
        onOpenChange={(o) => !o && setConfirm(false)}
        title="¿Eliminar meta?"
        message="Se borrarán la meta y su historial de aportes."
        loading={del.isPending}
        error={del.isError ? errorMessage(del.error) : null}
        onConfirm={() => goal && del.mutate(goal.id, { onSuccess: () => onOpenChange(false) })}
      />
    </>
  );
}
