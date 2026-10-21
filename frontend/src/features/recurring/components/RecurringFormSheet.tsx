import { useEffect, useState } from 'react';
import { Info } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { todayISO, weekdayDate } from '@/shared/lib/dates';
import { amountToDigits, formatMoney, fromCents, parseUserAmount, toCents } from '@/shared/lib/money';
import { positiveAmount } from '@/shared/lib/schemas';
import { Button, Chip, ConfirmSheet, Field, FormError, Input, Segmented, Select, Sheet, Switch, cn, errorMessage } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { useAccounts } from '../../accounts/hooks';
import { useCategories } from '../../categories/hooks';
import { useCreateRecurring, useDeleteRecurring, useUpdateRecurring } from '../hooks';
import {
  MAX_DAYS,
  modeFromRule,
  monthlyEquivalentCents,
  parseDays,
  scheduleFromMode,
  upcomingOccurrences,
  type DayValue,
  type ScheduleMode,
} from '../schedule';
import type { RecurringRule } from '../types';

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

/** Frecuencias clásicas que quedan bajo "Más opciones" (mensual y semanal tienen su propio chip). */
const MORE_FREQ = [
  { value: 'daily', label: 'Diaria' },
  { value: 'yearly', label: 'Anual' },
] as const;

const MODES: Array<{ value: ScheduleMode; label: string }> = [
  { value: 'q15L', label: 'Quincenal · 15 y último' },
  { value: 'q1530', label: 'Quincenal · 15 y 30' },
  { value: 'monthly', label: 'Mensual' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'custom', label: 'Días del mes…' },
  { value: 'more', label: 'Más opciones' },
];

const DAY_BUTTONS: DayValue[] = [...Array.from({ length: 31 }, (_, i) => i + 1), 'L'];

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
  const [mode, setMode] = useState<ScheduleMode>('monthly');
  const [customDays, setCustomDays] = useState<DayValue[]>([]);
  const [daysError, setDaysError] = useState(false);
  const [weekend, setWeekend] = useState(false);
  const [paycheck, setPaycheck] = useState(false);
  const mutation = rule ? update : create;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    getValues,
    watch,
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
    setMode(rule ? modeFromRule(rule) : 'monthly');
    setCustomDays(rule?.frequency === 'monthly_days' ? parseDays(rule.days_of_month) : []);
    setDaysError(false);
    setWeekend(rule?.weekend_adjust === 'previous_business_day');
    setPaycheck(rule?.is_paycheck ?? false);
    reset({
      amount: rule ? amountToDigits(rule.amount) : '',
      account_id: rule?.account_id ?? accounts.data?.[0]?.id ?? '',
      category_id: rule?.category_id ?? '',
      note: rule?.note ?? '',
      frequency: rule && rule.frequency !== 'monthly_days' ? rule.frequency : 'monthly',
      interval: String(rule?.interval ?? 1),
      start_date: rule?.start_date ?? today,
      end_date: rule?.end_date ?? '',
      active: rule?.active ?? true,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, rule, reset, today, accounts.data]);

  const cats = (categories.data ?? []).filter((c) => c.kind === type);

  const pickMode = (m: ScheduleMode) => {
    setMode(m);
    setDaysError(false);
    if (m === 'q15L' || m === 'q1530' || m === 'custom') setValue('interval', '1');
    if (m === 'custom' && customDays.length === 0) setCustomDays(mode === 'q1530' ? [15, 30] : mode === 'q15L' ? [15, 'L'] : []);
    if (m === 'more') {
      const f = getValues('frequency');
      if (f !== 'daily' && f !== 'yearly') setValue('frequency', 'daily');
    }
  };

  const toggleDay = (d: DayValue) => {
    setDaysError(false);
    setCustomDays((cur) => (cur.includes(d) ? cur.filter((x) => x !== d) : cur.length < MAX_DAYS ? [...cur, d] : cur));
  };

  // Vista previa: mismos cálculos que el contrato del API (ver schedule.ts).
  const [wAmount, wFreq, wInterval, wStart, wEnd, wAccount] = watch(['amount', 'frequency', 'interval', 'start_date', 'end_date', 'account_id']);
  const schedule = scheduleFromMode(mode, customDays, wFreq === 'yearly' ? 'yearly' : 'daily');
  const intervalN = schedule.frequency === 'monthly_days' ? 1 : /^[1-9]\d{0,2}$/.test(wInterval) ? Number(wInterval) : 1;
  const amountStr = parseUserAmount(wAmount);
  const perMonthCents =
    amountStr && toCents(amountStr) > 0n
      ? monthlyEquivalentCents(toCents(amountStr), schedule.frequency, intervalN, parseDays(schedule.days_of_month).length)
      : null;
  const occurrences = upcomingOccurrences(
    { ...schedule, interval: intervalN, weekend_adjust: weekend ? 'previous_business_day' : 'none', start_date: wStart, end_date: wEnd || null },
    4,
    rule ? today : undefined,
  );
  const accountName = (accounts.data ?? []).find((a) => a.id === wAccount)?.name ?? '';

  const onSubmit = handleSubmit((v) => {
    if (mode === 'custom' && customDays.length === 0) {
      setDaysError(true);
      return;
    }
    const sched = scheduleFromMode(mode, customDays, v.frequency === 'yearly' ? 'yearly' : 'daily');
    const body = {
      type,
      amount: parseUserAmount(v.amount)!,
      account_id: v.account_id,
      category_id: v.category_id,
      note: v.note.trim() || null,
      frequency: sched.frequency,
      interval: sched.frequency === 'monthly_days' ? 1 : Number(v.interval),
      days_of_month: sched.days_of_month,
      weekend_adjust: weekend ? ('previous_business_day' as const) : ('none' as const),
      is_paycheck: type === 'income' && paycheck,
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
              if (t === 'expense') setPaycheck(false);
            }}
            options={[
              { value: 'expense', label: 'Gasto' },
              { value: 'income', label: 'Ingreso' },
            ]}
          />
          <div className="grid grid-cols-2 gap-2">
            <Field label="Nota" error={errors.note?.message}>
              {(p) => <Input {...p} placeholder="Ej. Netflix, Sueldo" maxLength={255} {...register('note')} />}
            </Field>
            <Field label="Monto por pago" error={errors.amount?.message}>
              {(p) => <Input {...p} inputMode="decimal" placeholder="39900" autoComplete="off" className="font-bold" {...register('amount')} />}
            </Field>
          </div>
          {perMonthCents !== null && amountStr && (
            <p role="status" className="flex items-center gap-2 rounded-ctl bg-[#E4ECFD] px-3 py-2.5 text-[13px] text-[#1E3A8A]">
              <Info size={16} aria-hidden="true" className="shrink-0" />
              <span>
                {formatMoney(amountStr, { symbol: false })} por pago ≈ {formatMoney(fromCents(perMonthCents))} al mes
              </span>
            </p>
          )}

          <div role="group" aria-label="¿Cada cuánto?" className="flex flex-col gap-2">
            <span className="text-xs font-semibold text-muted">¿Cada cuánto?</span>
            <div className="flex flex-wrap gap-2">
              {MODES.map((o) => (
                <Chip key={o.value} active={mode === o.value} className="h-10" onClick={() => pickMode(o.value)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            {mode === 'custom' && (
              <div className="flex flex-col gap-1.5 rounded-[14px] bg-bg p-3">
                <span id="days-hint" className="text-xs text-muted">
                  Elige hasta {MAX_DAYS} días del mes
                </span>
                <div role="group" aria-labelledby="days-hint" className="grid grid-cols-8 gap-1">
                  {DAY_BUTTONS.map((d) => {
                    const on = customDays.includes(d);
                    return (
                      <button
                        key={d}
                        type="button"
                        aria-pressed={on}
                        aria-label={d === 'L' ? 'Último día del mes' : `Día ${d}`}
                        onClick={() => toggleDay(d)}
                        className={cn('h-[34px] rounded-lg text-xs font-semibold', on ? 'bg-primary text-white' : 'bg-surface text-ink')}
                      >
                        {d === 'L' ? 'Últ.' : d}
                      </button>
                    );
                  })}
                </div>
                {daysError && (
                  <p role="alert" className="text-xs text-expense">
                    Elige al menos un día
                  </p>
                )}
              </div>
            )}
            {mode === 'more' && (
              <Field label="Frecuencia">
                {(p) => (
                  <Select {...p} {...register('frequency')}>
                    {MORE_FREQ.map((f) => (
                      <option key={f.value} value={f.value}>
                        {f.label}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            )}
            {(mode === 'monthly' || mode === 'weekly' || mode === 'more') && (
              <Field label="Cada cuántos" error={errors.interval?.message}>
                {(p) => <Input {...p} inputMode="numeric" {...register('interval')} />}
              </Field>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Inicia" error={errors.start_date?.message}>
              {(p) => <Input {...p} type="date" {...register('start_date')} />}
            </Field>
            <Field label="Termina (opcional)">{(p) => <Input {...p} type="date" {...register('end_date')} />}</Field>
          </div>

          <section aria-label="Próximos pagos" className="flex flex-col gap-1.5 rounded-[14px] border border-line px-3.5 py-3">
            <h3 className="text-xs font-semibold text-muted">Próximos pagos</h3>
            {occurrences.length === 0 ? (
              <p className="text-sm text-muted">Elige las fechas para ver los próximos pagos.</p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {occurrences.map((o) => (
                  <li key={o.nominal} className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-semibold">{weekdayDate(o.date)}</span>
                    <span className={cn('text-xs', o.adjusted ? 'text-[#9A3412]' : 'text-muted')}>{o.adjusted ? 'cae fin de semana → se adelanta' : accountName}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="flex flex-col">
            <Switch checked={weekend} onChange={setWeekend} label="Si cae en fin de semana, el viernes antes" description="Como suelen pagar la nómina en Colombia" />
            {type === 'income' && (
              <Switch checked={paycheck} onChange={setPaycheck} label="Es mi sueldo" description="Tus quincenas se miden de un pago al siguiente" />
            )}
          </div>

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
