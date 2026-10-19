export interface User {
  id: string;
  email: string;
  display_name: string | null;
  currency: string;
  timezone: string;
  created_at: string;
}

export interface UserUpdate {
  currency?: string;
  timezone?: string;
  display_name?: string;
}
