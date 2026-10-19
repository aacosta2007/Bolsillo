import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from './cn';

/** Chip seleccionable (filtros). */
export function Chip({
  active,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(
        'h-9 shrink-0 whitespace-nowrap rounded-full border px-3.5 text-[13px] font-semibold transition-colors',
        active ? 'border-primary bg-primary text-white' : 'border-line bg-surface text-ink hover:bg-bg',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

type Tone = 'ok' | 'warning' | 'danger';
const TONES: Record<Tone, string> = {
  ok: 'bg-primary-tint text-primary-hover',
  warning: 'bg-warning-chip text-warning-ink',
  danger: 'bg-danger-chip text-danger-ink',
};

/** Etiqueta de estado (no interactiva). */
export function StatusChip({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={cn('rounded-full px-2 py-1 text-xs font-bold', TONES[tone])}>{children}</span>;
}

/** Control segmentado (Gasto/Ingreso/Transferir, Ahorro/Recurrentes). */
export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
  tint = 'bg-[#F0F3F0]',
}: {
  value: T;
  onChange: (v: T) => void;
  options: Array<{ value: T; label: string }>;
  label: string;
  tint?: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn('grid gap-1 rounded-ctl2 p-1', tint)}
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={cn(
              'h-10 rounded-[10px] text-sm font-semibold transition-colors',
              on ? 'bg-surface text-ink shadow-[0_1px_3px_rgba(22,32,27,0.15)]' : 'text-muted',
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
