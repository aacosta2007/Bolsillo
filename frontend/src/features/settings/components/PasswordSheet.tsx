import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { z } from 'zod';
import { Button, Field, FormError, Input, Sheet, errorMessage } from '@/shared/ui';
import { authApi } from '@/features/auth/api';

const schema = z
  .object({
    current: z.string().min(1, 'Ingresa tu contraseña actual'),
    next: z.string().min(8, 'Usa al menos 8 caracteres'),
    confirm: z.string(),
  })
  .refine((v) => v.next === v.confirm, { path: ['confirm'], message: 'Las contraseñas no coinciden' })
  .refine((v) => v.next !== v.current, { path: ['next'], message: 'La nueva contraseña debe ser distinta a la actual' });
type Values = z.infer<typeof schema>;

export function PasswordSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const change = useMutation({ mutationFn: (v: Values) => authApi.changePassword(v.current, v.next) });
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { current: '', next: '', confirm: '' } });

  useEffect(() => {
    if (open) {
      reset();
      change.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, reset]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title="Cambiar contraseña">
      {change.isSuccess ? (
        <div className="flex flex-col gap-4">
          <p role="status" className="text-sm">
            Tu contraseña se actualizó correctamente.
          </p>
          <Button block onClick={() => onOpenChange(false)}>
            Listo
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit((v) => change.mutate(v))} noValidate className="flex flex-col gap-4">
          <FormError message={change.isError ? errorMessage(change.error) : null} />
          <Field label="Contraseña actual" error={errors.current?.message}>
            {(p) => <Input {...p} type="password" autoComplete="current-password" {...register('current')} />}
          </Field>
          <Field label="Nueva contraseña" error={errors.next?.message}>
            {(p) => <Input {...p} type="password" autoComplete="new-password" {...register('next')} />}
          </Field>
          <Field label="Repite la nueva contraseña" error={errors.confirm?.message}>
            {(p) => <Input {...p} type="password" autoComplete="new-password" {...register('confirm')} />}
          </Field>
          <Button type="submit" size="lg" block loading={change.isPending}>
            Cambiar contraseña
          </Button>
        </form>
      )}
    </Sheet>
  );
}
