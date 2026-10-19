import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ApiError } from '@/shared/api/client';
import { Button, Field, FormError, Input } from '@/shared/ui';
import { Shell } from '@/app/layout';
import { useAuth } from '../AuthContext';

const schema = z.object({
  email: z.string().min(1, 'Ingresa tu correo').email('Correo no válido'),
  password: z.string().min(1, 'Ingresa tu contraseña'),
});
type Values = z.infer<typeof schema>;

export function loginErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) return 'Demasiados intentos fallidos. Espera unos minutos antes de volver a intentarlo.';
    if (err.status === 401) return err.detail || 'Correo o contraseña incorrectos.';
    return err.detail;
  }
  return 'No pudimos conectar con el servidor. Revisa tu conexión.';
}

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const from = (location.state as { from?: string } | null)?.from ?? '/';
  if (status === 'authenticated') return <Navigate to={from} replace />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setServerError(null);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (e) {
      setServerError(loginErrorMessage(e));
    }
  });

  return (
    <Shell>
      <div className="flex flex-1 flex-col justify-center gap-8 overflow-y-auto px-5 py-10">
        <div className="flex flex-col items-center gap-3 text-center">
          <img src="/icons/icon.svg" alt="" width={72} height={72} className="rounded-[20px]" />
          <h1 className="font-display text-[34px] font-bold">Bolsillo</h1>
          <p className="text-sm text-muted">Tus finanzas personales, simples y en tu bolsillo.</p>
        </div>

        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4 rounded-xl2 bg-surface p-5">
          <FormError message={serverError} />
          <Field label="Correo electrónico" error={errors.email?.message}>
            {(p) => <Input {...p} type="email" autoComplete="email" inputMode="email" placeholder="tu@correo.com" {...register('email')} />}
          </Field>
          <Field label="Contraseña" error={errors.password?.message}>
            {(p) => <Input {...p} type="password" autoComplete="current-password" {...register('password')} />}
          </Field>
          <Button type="submit" size="lg" block loading={isSubmitting}>
            Iniciar sesión
          </Button>
        </form>
      </div>
    </Shell>
  );
}
