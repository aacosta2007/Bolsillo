import { useNavigate, useParams } from 'react-router-dom';
import { todayISO } from '@/shared/lib/dates';
import { ErrorState, Skeleton, errorMessage } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { useCreateTransaction, useTransaction, useUpdateTransaction } from '../hooks';
import { useLookups } from '../lookups';
import { TransactionForm } from '../components/TransactionForm';
import type { TransactionInput } from '../types';

export function TransactionFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const lookups = useLookups();
  const tx = useTransaction(id);
  const create = useCreateTransaction();
  const update = useUpdateTransaction();
  const mutation = id ? update : create;

  const goBack = () => (window.history.length > 1 ? navigate(-1) : navigate('/movimientos'));

  if (lookups.ready === false || (id && tx.isLoading)) {
    return (
      <div role="status" aria-label="Cargando" className="flex flex-col gap-4 p-5">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (id && tx.isError) return <div className="p-5"><ErrorState error={tx.error} onRetry={() => tx.refetch()} /></div>;

  const onSubmit = (input: TransactionInput) => {
    if (id) update.mutate({ id, ...input }, { onSuccess: () => navigate('/movimientos', { replace: true }) });
    else create.mutate(input, { onSuccess: () => navigate('/movimientos', { replace: true }) });
  };

  return (
    <TransactionForm
      key={id ?? 'new'}
      mode={id ? 'edit' : 'create'}
      accounts={lookups.accounts}
      categories={lookups.categories}
      initial={tx.data}
      today={todayISO(user?.timezone)}
      submitting={mutation.isPending}
      error={mutation.isError ? errorMessage(mutation.error) : null}
      onSubmit={onSubmit}
      onCancel={goBack}
    />
  );
}
