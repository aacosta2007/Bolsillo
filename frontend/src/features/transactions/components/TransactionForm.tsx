import { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Delete, X } from 'lucide-react';
import { amountToDigits, digitsToAmount, formatMoney } from '@/shared/lib/money';
import { Button, CategoryIcon, Field, FormError, IconButton, Input, Segmented, Select, cn } from '@/shared/ui';
import type { Account } from '../../accounts/types';
import type { Category } from '../../categories/types';
import type { Transaction, TransactionInput, TxType } from '../types';

const schema = z
  .object({
    type: z.enum(['expense', 'income', 'transfer']),
    digits: z.string(),
    category_id: z.string(),
    account_id: z.string().min(1, 'Elige una cuenta'),
    transfer_account_id: z.string(),
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Elige una fecha'),
    note: z.string().max(255, 'Máximo 255 caracteres'),
  })
  .superRefine((v, ctx) => {
    if (!/[1-9]/.test(v.digits)) ctx.addIssue({ code: 'custom', path: ['digits'], message: 'Ingresa un monto mayor a 0' });
    if (v.type === 'transfer') {
      if (!v.transfer_account_id) ctx.addIssue({ code: 'custom', path: ['transfer_account_id'], message: 'Elige la cuenta destino' });
      else if (v.transfer_account_id === v.account_id)
        ctx.addIssue({ code: 'custom', path: ['transfer_account_id'], message: 'La cuenta destino debe ser distinta al origen' });
    } else if (!v.category_id) {
      ctx.addIssue({ code: 'custom', path: ['category_id'], message: 'Elige una categoría' });
    }
  });
type Values = z.infer<typeof schema>;

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '000', '0', '⌫'] as const;
const MAX_DIGITS = 12;

export function pressKey(current: string, key: string): string {
  if (key === '⌫') return current.slice(0, -1);
  return (current + key).replace(/^0+/, '').slice(0, MAX_DIGITS);
}

export interface TransactionFormProps {
  mode: 'create' | 'edit';
  accounts: Account[];
  categories: Category[];
  initial?: Transaction;
  today: string;
  submitting?: boolean;
  error?: string | null;
  onSubmit: (input: TransactionInput) => void;
  onCancel: () => void;
}

export function TransactionForm({ mode, accounts, categories, initial, today, submitting, error, onSubmit, onCancel }: TransactionFormProps) {
  // Cuentas archivadas no aceptan movimientos nuevos; se conserva la actual al editar.
  const usable = useMemo(
    () => accounts.filter((a) => !a.archived || a.id === initial?.account_id || a.id === initial?.transfer_account_id),
    [accounts, initial],
  );

  const defaultAccountId = accounts.find((a) => !a.archived)?.id ?? '';
  const defaults = useMemo<Values>(
    () => ({
      type: initial?.type ?? 'expense',
      digits: initial ? amountToDigits(initial.amount) : '',
      category_id: initial?.category_id ?? '',
      account_id: initial?.account_id ?? defaultAccountId,
      transfer_account_id: initial?.transfer_account_id ?? '',
      date: initial?.date ?? today,
      note: initial?.note ?? '',
    }),
    [initial, defaultAccountId, today],
  );

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: defaults });

  // Al cargar (o cargar la edición) reinicia con los valores correctos.
  useEffect(() => {
    reset(defaults);
  }, [defaults, reset]);

  const type = watch('type');
  const digits = watch('digits');
  const categoryId = watch('category_id');

  const visibleCats = useMemo(() => (type === 'transfer' ? [] : categories.filter((c) => c.kind === type)), [categories, type]);

  const setType = (t: TxType) => {
    setValue('type', t);
    setValue('category_id', '');
    if (t !== 'transfer') setValue('transfer_account_id', '');
  };

  const amountText =
    (type === 'expense' ? '− ' : type === 'income' ? '+ ' : '') + formatMoney(digitsToAmount(digits));
  const amountColor = type === 'expense' ? 'text-expense' : type === 'income' ? 'text-income' : 'text-ink';

  const submit = handleSubmit((v) => {
    const isTransfer = v.type === 'transfer';
    onSubmit({
      type: v.type,
      amount: digitsToAmount(v.digits),
      date: v.date,
      account_id: v.account_id,
      category_id: isTransfer ? null : v.category_id,
      transfer_account_id: isTransfer ? v.transfer_account_id : null,
      note: v.note.trim() || null,
    });
  });

  return (
    <form onSubmit={submit} noValidate className="flex min-h-full flex-col">
      <div className="flex items-center justify-between px-5 pt-4">
        <IconButton label="Cerrar" variant="soft" onClick={onCancel}>
          <X size={20} aria-hidden="true" />
        </IconButton>
        <h1 className="text-base font-bold">{mode === 'edit' ? 'Editar movimiento' : 'Nuevo movimiento'}</h1>
        <span className="w-11" />
      </div>

      <div className="px-5 pt-4">
        <Segmented
          label="Tipo de movimiento"
          value={type}
          onChange={setType}
          options={[
            { value: 'expense', label: 'Gasto' },
            { value: 'income', label: 'Ingreso' },
            { value: 'transfer', label: 'Transferir' },
          ]}
        />
      </div>

      <div className="flex flex-col items-center gap-1 px-5 pb-1.5 pt-5">
        <span id="amount-label" className="text-[13px] text-muted">
          Monto
        </span>
        <output
          aria-labelledby="amount-label"
          data-testid="amount"
          className={cn('tnum font-display text-[46px] font-bold tracking-[-1px]', amountColor)}
        >
          {amountText}
        </output>
        {errors.digits && (
          <p role="alert" className="text-xs text-expense">
            {errors.digits.message}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2.5 px-5 pt-2">
        <FormError message={error} />

        {type !== 'transfer' && (
          <fieldset className="flex flex-col gap-2.5">
            <legend className="mb-2.5 text-[13px] font-semibold text-muted">Categoría</legend>
            {visibleCats.length === 0 ? (
              <p className="rounded-ctl bg-bg px-3 py-3 text-sm text-muted">
                No tienes categorías de {type === 'expense' ? 'gasto' : 'ingreso'}. Crea una en{' '}
                <Link to="/ajustes" className="font-semibold text-primary underline">
                  Ajustes
                </Link>
                .
              </p>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {visibleCats.map((c) => {
                  const on = c.id === categoryId;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setValue('category_id', c.id, { shouldValidate: true })}
                      className={cn(
                        'flex min-h-[64px] flex-col items-center justify-center gap-1 rounded-ctl2 border-2 px-1 py-1.5 text-xs font-semibold',
                        on ? 'border-primary bg-primary-tint' : 'border-line-soft bg-surface',
                      )}
                    >
                      <span
                        aria-hidden="true"
                        className="flex h-[26px] w-[26px] items-center justify-center rounded-lg text-white"
                        style={{ background: c.color || '#55615B' }}
                      >
                        <CategoryIcon name={c.icon} size={14} />
                      </span>
                      <span className="w-full truncate text-center">{c.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
            {errors.category_id && (
              <p role="alert" className="text-xs text-expense">
                {errors.category_id.message}
              </p>
            )}
          </fieldset>
        )}

        {usable.length === 0 ? (
          <p className="rounded-ctl bg-bg px-3 py-3 text-sm text-muted">
            Aún no tienes cuentas. Crea una en{' '}
            <Link to="/ajustes" className="font-semibold text-primary underline">
              Ajustes
            </Link>{' '}
            para registrar movimientos.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            <Field label={type === 'transfer' ? 'Desde' : 'Cuenta'} error={errors.account_id?.message}>
              {(p) => (
                <Select {...p} {...register('account_id')}>
                  {usable.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            {type === 'transfer' ? (
              <Field label="Hacia" error={errors.transfer_account_id?.message}>
                {(p) => (
                  <Select {...p} {...register('transfer_account_id')}>
                    <option value="">Selecciona…</option>
                    {usable
                      .filter((a) => !a.archived)
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </Select>
                )}
              </Field>
            ) : (
              <Field label="Fecha" error={errors.date?.message}>
                {(p) => <Input {...p} type="date" {...register('date')} />}
              </Field>
            )}
          </div>
        )}

        {type === 'transfer' && (
          <Field label="Fecha" error={errors.date?.message}>
            {(p) => <Input {...p} type="date" {...register('date')} />}
          </Field>
        )}

        <Field label="Nota" error={errors.note?.message}>
          {(p) => <Input {...p} type="text" placeholder="Ej. almuerzo con el equipo" maxLength={255} {...register('note')} />}
        </Field>
      </div>

      <div className="flex-1" />

      <div role="group" aria-label="Teclado numérico" className="grid grid-cols-3 gap-1.5 px-5 pb-1.5 pt-3">
        {KEYS.map((k) => (
          <button
            key={k}
            type="button"
            aria-label={k === '⌫' ? 'Borrar' : k}
            onClick={() => setValue('digits', pressKey(digits, k), { shouldValidate: errors.digits !== undefined })}
            className="flex h-12 items-center justify-center rounded-ctl bg-bg text-xl font-semibold hover:bg-line-soft active:bg-line"
          >
            {k === '⌫' ? <Delete size={22} aria-hidden="true" /> : k}
          </button>
        ))}
      </div>
      <div className="px-5 pb-6 pt-1.5 pb-safe">
        <Button type="submit" size="lg" block loading={submitting} disabled={usable.length === 0}>
          {mode === 'edit' ? 'Guardar cambios' : 'Guardar movimiento'}
        </Button>
      </div>
    </form>
  );
}
