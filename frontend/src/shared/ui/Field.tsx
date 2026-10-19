import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { cn } from './cn';

const CONTROL =
  'w-full rounded-ctl border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted/70 disabled:bg-bg disabled:opacity-70';

interface FieldProps {
  label: string;
  error?: string;
  hint?: string;
  children: (props: { id: string; 'aria-invalid': boolean; 'aria-describedby'?: string }) => ReactNode;
  className?: string;
}

/** Label + control + mensaje de error accesibles. */
export function Field({ label, error, hint, children, className }: FieldProps) {
  const id = useId();
  const msgId = `${id}-msg`;
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      {children({ id, 'aria-invalid': !!error, 'aria-describedby': error || hint ? msgId : undefined })}
      {(error || hint) && (
        <p id={msgId} role={error ? 'alert' : undefined} className={cn('text-xs', error ? 'text-expense' : 'text-muted')}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...rest }, ref) {
  return <input ref={ref} className={cn(CONTROL, 'h-11', 'aria-[invalid=true]:border-expense', className)} {...rest} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className, ...rest },
  ref,
) {
  return <select ref={ref} className={cn(CONTROL, 'h-11 aria-[invalid=true]:border-expense', className)} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, ...rest },
  ref,
) {
  return <textarea ref={ref} className={cn(CONTROL, 'min-h-[88px] py-2', className)} {...rest} />;
});

export function FormError({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-ctl bg-expense-tint px-3 py-2 text-sm text-danger-ink">
      {message}
    </p>
  );
}
