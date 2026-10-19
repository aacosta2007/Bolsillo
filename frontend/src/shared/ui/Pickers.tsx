import { Check } from 'lucide-react';
import { CategoryIcon, ICON_NAMES } from './CategoryIcon';
import { cn } from './cn';

export const PALETTE = ['#0F5E55', '#C2410C', '#2563EB', '#F2A65A', '#93C5BB', '#6D28D9', '#BE185D', '#0E7490', '#B7791F', '#55615B'];

export function ColorPicker({ value, onChange, label = 'Color' }: { value: string; onChange: (c: string) => void; label?: string }) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-xs font-semibold text-muted">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {PALETTE.map((c) => (
          <button
            key={c}
            type="button"
            aria-label={`Color ${c}`}
            aria-pressed={value.toLowerCase() === c.toLowerCase()}
            onClick={() => onChange(c)}
            className="flex h-11 w-11 items-center justify-center rounded-full text-white"
            style={{ background: c }}
          >
            {value.toLowerCase() === c.toLowerCase() && <Check size={18} aria-hidden="true" />}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function IconPicker({ value, onChange, color }: { value: string; onChange: (n: string) => void; color: string }) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-xs font-semibold text-muted">Icono</legend>
      <div className="grid grid-cols-6 gap-2">
        {ICON_NAMES.map((n) => {
          const on = n === value;
          return (
            <button
              key={n}
              type="button"
              aria-label={`Icono ${n}`}
              aria-pressed={on}
              onClick={() => onChange(n)}
              className={cn(
                'flex h-11 w-full items-center justify-center rounded-ctl border-2',
                on ? 'border-primary bg-primary-tint' : 'border-line-soft bg-surface',
              )}
              style={on ? { color } : undefined}
            >
              <CategoryIcon name={n} size={20} />
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
