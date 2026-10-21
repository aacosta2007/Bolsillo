import { useId } from 'react';
import { cn } from './cn';

/** Interruptor accesible (role="switch") con título y descripción. */
export function Switch({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  const descId = useId();
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-describedby={description ? descId : undefined}
      onClick={() => onChange(!checked)}
      className="flex min-h-[52px] w-full items-center gap-3 text-left"
    >
      <span className="flex flex-1 flex-col">
        <span className="text-sm font-semibold">{label}</span>
        {description && (
          <span id={descId} className="text-xs text-muted">
            {description}
          </span>
        )}
      </span>
      <span
        aria-hidden="true"
        className={cn('flex h-7 w-[46px] shrink-0 items-center rounded-full p-[3px] transition-colors', checked ? 'justify-end bg-primary' : 'justify-start bg-[#C9D1CC]')}
      >
        <span className="h-[22px] w-[22px] rounded-full bg-white" />
      </span>
    </button>
  );
}
