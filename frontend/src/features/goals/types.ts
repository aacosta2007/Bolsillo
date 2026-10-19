export interface Goal {
  id: string;
  name: string;
  target_amount: string;
  target_date: string | null;
  account_id: string | null;
  color: string | null;
  icon: string | null;
  saved: string;
  percent: number;
  monthly_needed: string | null;
  completed: boolean;
  created_at: string;
}

export interface GoalInput {
  name: string;
  target_amount: string;
  target_date?: string | null;
  account_id?: string | null;
  color?: string;
  icon?: string;
}

export interface Contribution {
  id: string;
  goal_id: string;
  amount: string;
  date: string;
  note: string | null;
}

export interface ContributionInput {
  amount: string;
  date: string;
  note?: string | null;
}
