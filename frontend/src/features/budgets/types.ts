export type BudgetState = 'ok' | 'warning' | 'exceeded';

export interface BudgetStatus {
  id: string;
  category_id: string;
  month: string;
  amount_limit: string;
  alert_threshold: string;
  spent: string;
  remaining: string;
  percent: number;
  status: BudgetState;
}

export interface BudgetInput {
  category_id: string;
  month: string;
  amount_limit: string;
  alert_threshold?: number;
}
