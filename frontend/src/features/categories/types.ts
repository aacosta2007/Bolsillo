export type CategoryKind = 'income' | 'expense';

export interface Category {
  id: string;
  name: string;
  kind: CategoryKind;
  icon: string | null;
  color: string | null;
  parent_id: string | null;
}

export interface CategoryInput {
  name: string;
  kind: CategoryKind;
  icon?: string;
  color?: string;
  parent_id?: string | null;
}
