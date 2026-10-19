import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Pencil, Trash2 } from 'lucide-react';
import { formatDateLong } from '@/shared/lib/dates';
import { Button, ConfirmSheet, Money, Sheet, errorMessage } from '@/shared/ui';
import type { Lookups } from '../lookups';
import { useDeleteTransaction } from '../hooks';
import type { Transaction } from '../types';
import { txTitle } from './TransactionRow';

const TYPE_LABEL = { expense: 'Gasto', income: 'Ingreso', transfer: 'Transferencia' } as const;

export function TransactionDetailSheet({
  tx,
  lookups,
  onClose,
}: {
  tx: Transaction | null;
  lookups: Pick<Lookups, 'categoryMap' | 'accountMap'>;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const del = useDeleteTransaction();
  const [confirming, setConfirming] = useState(false);

  const close = () => {
    setConfirming(false);
    del.reset();
    onClose();
  };

  if (!tx) return null;
  const cat = tx.category_id ? lookups.categoryMap.get(tx.category_id) : undefined;
  const acc = lookups.accountMap.get(tx.account_id);
  const dest = tx.transfer_account_id ? lookups.accountMap.get(tx.transfer_account_id) : undefined;

  const rows: Array<[string, string | undefined]> = [
    ['Tipo', TYPE_LABEL[tx.type]],
    ['Fecha', formatDateLong(tx.date)],
    tx.type === 'transfer' ? ['Desde', acc?.name] : ['Cuenta', acc?.name],
    ...(tx.type === 'transfer' ? ([['Hacia', dest?.name]] as Array<[string, string | undefined]>) : []),
    ...(cat ? ([['Categoría', cat.name]] as Array<[string, string | undefined]>) : []),
    ['Nota', tx.note || undefined],
  ];

  return (
    <>
      <Sheet open={!confirming} onOpenChange={(o) => !o && close()} title={txTitle(tx, lookups.categoryMap, lookups.accountMap)}>
        <div className="flex flex-col gap-4">
          <Money value={tx.amount} type={tx.type} className="font-display text-[34px] font-bold" />
          <dl className="flex flex-col divide-y divide-line-soft rounded-ctl2 border border-line-soft px-3.5">
            {rows
              .filter(([, v]) => v)
              .map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
                  <dt className="text-muted">{k}</dt>
                  <dd className="text-right font-semibold">{v}</dd>
                </div>
              ))}
            {tx.recurring_id && (
              <div className="py-2.5 text-xs text-muted">Generado por un movimiento recurrente.</div>
            )}
          </dl>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" onClick={() => navigate(`/movimientos/${tx.id}/editar`)}>
              <Pencil size={16} aria-hidden="true" />
              Editar
            </Button>
            <Button variant="secondary" className="text-expense" onClick={() => setConfirming(true)}>
              <Trash2 size={16} aria-hidden="true" />
              Eliminar
            </Button>
          </div>
        </div>
      </Sheet>
      <ConfirmSheet
        open={confirming}
        onOpenChange={(o) => !o && setConfirming(false)}
        title="¿Eliminar movimiento?"
        message="Esta acción no se puede deshacer y se ajustarán los saldos de tus cuentas."
        loading={del.isPending}
        error={del.isError ? errorMessage(del.error) : null}
        onConfirm={() => del.mutate(tx.id, { onSuccess: close })}
      />
    </>
  );
}
