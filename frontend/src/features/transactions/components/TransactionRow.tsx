import { ArrowLeftRight } from 'lucide-react';
import { CategoryIcon, Money, cn } from '@/shared/ui';
import type { Account } from '../../accounts/types';
import type { Category } from '../../categories/types';
import type { Transaction } from '../types';

const TINT = {
  expense: 'bg-expense-tint text-[#9A3412]',
  income: 'bg-income-tint text-income',
  transfer: 'bg-[#ECEFEC] text-[#3D4843]',
} as const;

export function txTitle(tx: Transaction, cats: Map<string, Category>, accs: Map<string, Account>): string {
  if (tx.note) return tx.note;
  if (tx.type === 'transfer') {
    return `${accs.get(tx.account_id)?.name ?? 'Cuenta'} → ${accs.get(tx.transfer_account_id ?? '')?.name ?? 'Cuenta'}`;
  }
  return cats.get(tx.category_id ?? '')?.name ?? 'Movimiento';
}

export function TransactionRow({
  tx,
  categoryMap,
  accountMap,
  onClick,
  trailingMeta,
}: {
  tx: Transaction;
  categoryMap: Map<string, Category>;
  accountMap: Map<string, Account>;
  onClick?: () => void;
  /** Texto extra al final de la línea secundaria (p. ej. fecha). */
  trailingMeta?: string;
}) {
  const cat = tx.category_id ? categoryMap.get(tx.category_id) : undefined;
  const acc = accountMap.get(tx.account_id);
  const meta = [tx.type === 'transfer' ? 'Transferencia' : cat?.name, tx.type === 'transfer' ? undefined : acc?.name, trailingMeta]
    .filter(Boolean)
    .join(' · ');

  const inner = (
    <>
      <span aria-hidden="true" className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px]', TINT[tx.type])}>
        {tx.type === 'transfer' ? <ArrowLeftRight size={18} /> : <CategoryIcon name={cat?.icon} size={18} />}
      </span>
      <span className="flex min-w-0 flex-1 flex-col text-left">
        <span className="truncate text-sm font-semibold">{txTitle(tx, categoryMap, accountMap)}</span>
        <span className="truncate text-xs text-muted">{meta}</span>
      </span>
      <Money value={tx.amount} type={tx.type} className="text-sm font-bold" />
    </>
  );

  const cls = 'flex min-h-[56px] w-full items-center gap-3 py-2';
  return onClick ? (
    <button type="button" onClick={onClick} className={cn(cls, 'rounded-ctl text-left hover:bg-bg/60')}>
      {inner}
    </button>
  ) : (
    <div className={cls}>{inner}</div>
  );
}
