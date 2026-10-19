export type TxType = 'income' | 'expense' | 'transfer';

export interface Transaction {
  id: string;
  type: TxType;
  amount: string;
  date: string;
  account_id: string;
  category_id: string | null;
  transfer_account_id: string | null;
  note: string | null;
  recurring_id: string | null;
  created_at: string;
}

export interface TransactionInput {
  type: TxType;
  amount: string;
  date: string;
  account_id: string;
  category_id?: string | null;
  transfer_account_id?: string | null;
  note?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface TransactionFilters {
  from?: string;
  to?: string;
  account_id?: string;
  category_id?: string;
  type?: TxType;
  q?: string;
}
