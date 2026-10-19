import { cn } from './cn';

export function ProgressBar({
  percent,
  color,
  trackClass = 'bg-line-soft',
  height = 8,
  label,
}: {
  percent: number;
  /** Clase tailwind (bg-*) o color CSS. */
  color: string;
  trackClass?: string;
  height?: number;
  label?: string;
}) {
  const w = Math.max(0, Math.min(100, percent));
  const isClass = color.startsWith('bg-');
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(w)}
      aria-label={label}
      className={cn('overflow-hidden rounded-full', trackClass)}
      style={{ height }}
    >
      <div
        className={cn('h-full rounded-full', isClass && color)}
        style={{ width: `${w}%`, background: isClass ? undefined : color }}
      />
    </div>
  );
}
