export type AccountType = 'cash' | 'bank' | 'credit_card' | 'savings' | 'wallet';

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  initial_balance: string;
  color: string | null;
  icon: string | null;
  archived: boolean;
  balance: string;
  created_at: string;
}

export interface AccountInput {
  name: string;
  type: AccountType;
  initial_balance?: string;
  color?: string;
  icon?: string;
}

export const ACCOUNT_TYPES: Array<{ value: AccountType; label: string; icon: string }> = [
  { value: 'cash', label: 'Efectivo', icon: 'banknote' },
  { value: 'bank', label: 'Cuenta bancaria', icon: 'landmark' },
  { value: 'credit_card', label: 'Tarjeta de crédito', icon: 'credit-card' },
  { value: 'savings', label: 'Ahorros', icon: 'piggy-bank' },
  { value: 'wallet', label: 'Billetera digital', icon: 'wallet' },
];
