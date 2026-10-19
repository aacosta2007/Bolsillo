import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from './cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'dashed';

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:bg-primary-hover disabled:opacity-50',
  secondary: 'border border-line bg-surface text-ink hover:bg-bg disabled:opacity-50',
  ghost: 'bg-transparent text-primary hover:bg-primary-tint disabled:opacity-50',
  danger: 'bg-expense text-white hover:opacity-90 disabled:opacity-50',
  dashed: 'border border-dashed border-[#A9B5AE] bg-transparent text-primary hover:bg-primary-tint disabled:opacity-50',
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  block?: boolean;
  size?: 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = 'primary', loading, block, size = 'md', className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-ctl2 px-4 text-sm font-bold transition-colors disabled:cursor-not-allowed',
        size === 'md' ? 'min-h-[48px]' : 'min-h-[54px] rounded-2xl text-base',
        block && 'w-full',
        VARIANTS[variant],
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
});

export const IconButton = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { label: string; variant?: 'outline' | 'primary' | 'soft' }
>(function IconButton({ label, variant = 'outline', className, children, type = 'button', ...rest }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-ctl2 transition-colors',
        variant === 'outline' && 'border border-line bg-surface text-ink hover:bg-bg',
        variant === 'primary' && 'bg-primary text-white hover:bg-primary-hover',
        variant === 'soft' && 'bg-bg text-ink hover:bg-line-soft',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
});
