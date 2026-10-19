import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { Button, Card, CardHeader, Field, FormError, Input, Select, errorMessage } from '@/shared/ui';
import { authApi } from '@/features/auth/api';
import { useAuth } from '@/features/auth/AuthContext';

const CURRENCIES = ['COP', 'USD', 'EUR', 'MXN', 'PEN', 'CLP', 'ARS'];
const ZONES = [
  'America/Bogota',
  'America/Mexico_City',
  'America/Lima',
  'America/Santiago',
  'America/Argentina/Buenos_Aires',
  'America/New_York',
  'Europe/Madrid',
  'UTC',
];

const schema = z.object({
  display_name: z.string().trim().max(100),
  currency: z.string().min(3),
  timezone: z.string().min(1),
});
type Values = z.infer<typeof schema>;

export function ProfileSection() {
  const { user, setUser } = useAuth();
  const [saved, setSaved] = useState(false);
  const save = useMutation({ mutationFn: authApi.updateMe, onSuccess: (u) => (setUser(u), setSaved(true)) });
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { display_name: user?.display_name ?? '', currency: user?.currency ?? 'COP', timezone: user?.timezone ?? 'America/Bogota' },
  });

  const zones = user && !ZONES.includes(user.timezone) ? [user.timezone, ...ZONES] : ZONES;
  const currencies = user && !CURRENCIES.includes(user.currency) ? [user.currency, ...CURRENCIES] : CURRENCIES;

  return (
    <Card>
      <CardHeader title="Perfil" aside={user?.email} />
      <form
        noValidate
        className="flex flex-col gap-3"
        onSubmit={handleSubmit((v) => {
          setSaved(false);
          save.mutate({ display_name: v.display_name.trim(), currency: v.currency, timezone: v.timezone });
        })}
      >
        <FormError message={save.isError ? errorMessage(save.error) : null} />
        <Field label="Nombre" error={errors.display_name?.message}>
          {(p) => <Input {...p} autoComplete="name" {...register('display_name')} />}
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Moneda">
            {(p) => (
              <Select {...p} {...register('currency')}>
                {currencies.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Zona horaria">
            {(p) => (
              <Select {...p} {...register('timezone')}>
                {zones.map((z) => (
                  <option key={z}>{z}</option>
                ))}
              </Select>
            )}
          </Field>
        </div>
        {saved && (
          <p role="status" className="text-sm text-primary">
            Perfil actualizado.
          </p>
        )}
        <Button type="submit" loading={save.isPending}>
          Guardar perfil
        </Button>
      </form>
    </Card>
  );
}
