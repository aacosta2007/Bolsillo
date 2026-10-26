import type { Page } from '@/features/transactions/types';

export type NotificationKind =
  | 'budget_warning'
  | 'budget_exceeded'
  | 'upcoming_recurring'
  | 'payday'
  | 'monthly_report'
  | 'test';

export interface AppNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string;
  url: string | null;
  read: boolean;
  created_at: string;
}

export interface NotificationsPage extends Page<AppNotification> {
  unread_count: number;
}

export interface NotificationPreferences {
  budget_alerts: boolean;
  upcoming_alerts: boolean;
  upcoming_days_before: number;
  payday_alerts: boolean;
  monthly_report_alerts: boolean;
  notify_hour: number;
}

export interface PushSubscriptionInfo {
  id: string;
  endpoint: string;
  device: string | null;
  created_at: string;
}

export interface PushSubscriptionInput {
  endpoint: string;
  keys: { p256dh: string; auth: string };
  device?: string;
}

export interface TestResult {
  sent: number;
  failed: number;
}
