import type { ReactNode } from 'react';
import { Inbox, TriangleAlert } from 'lucide-react';
import { ApiError } from '../api/client';
import { Button } from './Button';
import { cn } from './cn';

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('animate-pulse rounded-ctl bg-line/70', className)} />;
}

export function ListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Cargando" className="flex flex-col gap-3 rounded-card bg-surface p-4">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-[12px]" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-3.5 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
          </div>
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
  icon,
}: {
  title: string;
  message?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card bg-surface px-6 py-10 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-tint text-primary">
        {icon ?? <Inbox size={22} aria-hidden="true" />}
      </span>
      <h3 className="text-base font-bold">{title}</h3>
      {message && <p className="max-w-[280px] text-sm text-muted">{message}</p>}
      {action}
    </div>
  );
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.detail;
  if (err instanceof Error) return err.message;
  return 'Ocurrió un error inesperado.';
}

export function ErrorState({ error, onRetry }: { error?: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-card bg-surface px-6 py-8 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-expense-tint text-expense">
        <TriangleAlert size={22} aria-hidden="true" />
      </span>
      <h3 className="text-base font-bold">No pudimos cargar esto</h3>
      <p className="max-w-[300px] text-sm text-muted">{error ? errorMessage(error) : 'Revisa tu conexión e inténtalo de nuevo.'}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}
