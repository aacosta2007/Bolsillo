import { formatMoney, formatSigned, type TxKind } from '../lib/money';
import { cn } from './cn';

const COLOR: Record<TxKind, string> = {
  income: 'text-income',
  expense: 'text-expense',
  transfer: 'text-[#3D4843]',
};

/** Monto con signo y color según tipo de movimiento. */
export function Money({
  value,
  type,
  className,
}: {
  value: string | number;
  type?: TxKind;
  className?: string;
}) {
  return (
    <span className={cn('tnum whitespace-nowrap', type && COLOR[type], className)}>
      {type ? formatSigned(type, value) : formatMoney(value)}
    </span>
  );
}
