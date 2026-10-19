import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { amountToDigits, parseUserAmount, parseMoney } from '@/shared/lib/money';
import { nonNegativeAmount } from '@/shared/lib/schemas';
import { ApiError } from '@/shared/api/client';
import { Button, ColorPicker, ConfirmSheet, Field, FormError, IconPicker, Input, Select, Sheet, errorMessage } from '@/shared/ui';
import { useCreateAccount, useDeleteAccount, useUpdateAccount } from '../hooks';
import { ACCOUNT_TYPES, type Account, type AccountType } from '../types';

const schema = z.object({
  name: z.string().trim().min(1, 'Ponle un nombre a la cuenta').max(100),
  type: z.enum(['cash', 'bank', 'credit_card', 'savings', 'wallet']),
  initial_balance: nonNegativeAmount('Saldo no válido'),
});
type Values = z.infer<typeof schema>;

export function AccountFormSheet({ open, onOpenChange, account }: { open: boolean; onOpenChange: (o: boolean) => void; account: Account | null }) {
  const create = useCreateAccount();
  const update = useUpdateAccount();
  const del = useDeleteAccount();
  const [color, setColor] = useState('#0F5E55');
  const [icon, setIcon] = useState('wallet');
  const [confirm, setConfirm] = useState(false);
  const mutation = account ? update : create;

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { name: '', type: 'bank', initial_balance: '' } });
  const type = watch('type');

  useEffect(() => {
    if (!open) return;
    create.reset();
    update.reset();
    del.reset();
    setConfirm(false);
    setColor(account?.color ?? '#0F5E55');
    setIcon(account?.icon ?? 'landmark');
    reset({
      name: account?.name ?? '',
      type: account?.type ?? 'bank',
      initial_balance: account && !/^0+(\.0+)?$/.test(account.initial_balance) ? amountToDigits(account.initial_balance) : '',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, account, reset]);

  const onSubmit = handleSubmit((v) => {
    const initial = v.initial_balance.trim() ? parseUserAmount(v.initial_balance)! : '0.00';
    const body = { name: v.name.trim(), type: v.type as AccountType, initial_balance: initial, color, icon };
    const done = { onSuccess: () => onOpenChange(false) };
    if (account) update.mutate({ id: account.id, ...body }, done);
    else create.mutate(body, done);
  });

  const deleteConflict = del.error instanceof ApiError && del.error.status === 409;
  const bal = account ? parseMoney(account.balance) : null;

  return (
    <>
      <Sheet open={open && !confirm} onOpenChange={onOpenChange} title={account ? 'Editar cuenta' : 'Nueva cuenta'}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <FormError message={mutation.isError ? errorMessage(mutation.error) : null} />
          <Field label="Nombre" error={errors.name?.message}>
            {(p) => <Input {...p} placeholder="Ej. Bancolombia" maxLength={100} {...register('name')} />}
          </Field>
          <Field label="Tipo">
            {(p) => (
              <Select
                {...p}
                {...register('type', {
                  onChange: (e) => {
                    const t = ACCOUNT_TYPES.find((x) => x.value === e.target.value);
                    if (t && !account) setIcon(t.icon);
                  },
                })}
              >
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field
            label={type === 'credit_card' ? 'Saldo inicial (usa cero si no tienes deuda)' : 'Saldo inicial (COP)'}
            error={errors.initial_balance?.message}
            hint={account ? 'Modificarlo ajusta el saldo actual de la cuenta.' : undefined}
          >
            {(p) => <Input {...p} inputMode="decimal" placeholder="0" autoComplete="off" {...register('initial_balance')} />}
          </Field>
          <ColorPicker value={color} onChange={setColor} />
          <IconPicker value={icon} onChange={setIcon} color={color} />
          <Button type="submit" size="lg" block loading={mutation.isPending}>
            Guardar cuenta
          </Button>
          {account && (
            <>
              <Button
                variant="secondary"
                block
                loading={update.isPending}
                onClick={() => update.mutate({ id: account.id, archived: !account.archived }, { onSuccess: () => onOpenChange(false) })}
              >
                {account.archived ? 'Restaurar cuenta' : 'Archivar cuenta'}
              </Button>
              <Button variant="secondary" block className="text-expense" onClick={() => setConfirm(true)}>
                Eliminar cuenta
              </Button>
              {bal && <p className="text-center text-xs text-muted">Archivar oculta la cuenta pero conserva sus movimientos.</p>}
            </>
          )}
        </form>
      </Sheet>
      <ConfirmSheet
        open={open && confirm}
        onOpenChange={(o) => !o && setConfirm(false)}
        title="¿Eliminar cuenta?"
        message="Solo se puede eliminar si no tiene movimientos. Si ya los tiene, archívala."
        loading={del.isPending}
        error={del.isError ? (deleteConflict ? 'Esta cuenta tiene movimientos: archívala en lugar de eliminarla.' : errorMessage(del.error)) : null}
        onConfirm={() => account && del.mutate(account.id, { onSuccess: () => onOpenChange(false) })}
      />
    </>
  );
}
