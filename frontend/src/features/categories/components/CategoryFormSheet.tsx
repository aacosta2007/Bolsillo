import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ApiError } from '@/shared/api/client';
import { Button, ColorPicker, ConfirmSheet, Field, FormError, IconPicker, Input, Segmented, Sheet, errorMessage } from '@/shared/ui';
import { useCreateCategory, useDeleteCategory, useUpdateCategory } from '../hooks';
import type { Category, CategoryKind } from '../types';

const schema = z.object({ name: z.string().trim().min(1, 'Ponle un nombre a la categoría').max(100) });
type Values = z.infer<typeof schema>;

export function CategoryFormSheet({
  open,
  onOpenChange,
  category,
  defaultKind,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  category: Category | null;
  defaultKind: CategoryKind;
}) {
  const create = useCreateCategory();
  const update = useUpdateCategory();
  const del = useDeleteCategory();
  const [kind, setKind] = useState<CategoryKind>(defaultKind);
  const [color, setColor] = useState('#0F5E55');
  const [icon, setIcon] = useState('tag');
  const [confirm, setConfirm] = useState(false);
  const mutation = category ? update : create;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { name: '' } });

  useEffect(() => {
    if (!open) return;
    create.reset();
    update.reset();
    del.reset();
    setConfirm(false);
    setKind(category?.kind ?? defaultKind);
    setColor(category?.color ?? '#0F5E55');
    setIcon(category?.icon ?? 'tag');
    reset({ name: category?.name ?? '' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, category, defaultKind, reset]);

  const onSubmit = handleSubmit((v) => {
    const done = { onSuccess: () => onOpenChange(false) };
    if (category) update.mutate({ id: category.id, name: v.name.trim(), color, icon }, done);
    else create.mutate({ name: v.name.trim(), kind, color, icon }, done);
  });

  const conflict = del.error instanceof ApiError && del.error.status === 409;

  return (
    <>
      <Sheet open={open && !confirm} onOpenChange={onOpenChange} title={category ? 'Editar categoría' : 'Nueva categoría'}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <FormError message={mutation.isError ? errorMessage(mutation.error) : null} />
          {!category && (
            <Segmented
              label="Tipo de categoría"
              value={kind}
              onChange={setKind}
              options={[
                { value: 'expense', label: 'Gasto' },
                { value: 'income', label: 'Ingreso' },
              ]}
            />
          )}
          <Field label="Nombre" error={errors.name?.message}>
            {(p) => <Input {...p} placeholder="Ej. Mascotas" maxLength={100} {...register('name')} />}
          </Field>
          <ColorPicker value={color} onChange={setColor} />
          <IconPicker value={icon} onChange={setIcon} color={color} />
          <Button type="submit" size="lg" block loading={mutation.isPending}>
            Guardar categoría
          </Button>
          {category && (
            <Button variant="secondary" block className="text-expense" onClick={() => setConfirm(true)}>
              Eliminar categoría
            </Button>
          )}
        </form>
      </Sheet>
      <ConfirmSheet
        open={open && confirm}
        onOpenChange={(o) => !o && setConfirm(false)}
        title="¿Eliminar categoría?"
        message="Solo se puede eliminar si no tiene movimientos ni presupuestos."
        loading={del.isPending}
        error={del.isError ? (conflict ? 'Esta categoría tiene movimientos o presupuestos y no se puede eliminar.' : errorMessage(del.error)) : null}
        onConfirm={() => category && del.mutate(category.id, { onSuccess: () => onOpenChange(false) })}
      />
    </>
  );
}
