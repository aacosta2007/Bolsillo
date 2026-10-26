import { api } from '@/shared/api/client';
import type {
  NotificationPreferences,
  NotificationsPage,
  PushSubscriptionInfo,
  PushSubscriptionInput,
  TestResult,
} from './types';

export const notificationsApi = {
  list: (pageSize = 30, unreadOnly = false) =>
    api<NotificationsPage>('/notifications', { query: { unread_only: unreadOnly, page: 1, page_size: pageSize } }),
  markRead: (id: string) => api<void>(`/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => api<void>('/notifications/read-all', { method: 'POST' }),
  preferences: () => api<NotificationPreferences>('/notifications/preferences'),
  updatePreferences: (body: Partial<NotificationPreferences>) =>
    api<NotificationPreferences>('/notifications/preferences', { method: 'PATCH', body }),
  sendTest: () => api<TestResult>('/notifications/test', { method: 'POST' }),
  vapidPublicKey: () => api<{ public_key: string }>('/notifications/vapid-public-key'),
  subscribe: (body: PushSubscriptionInput) => api<PushSubscriptionInfo>('/notifications/subscriptions', { method: 'POST', body }),
  unsubscribe: (endpoint: string) => api<void>('/notifications/subscriptions', { method: 'DELETE', query: { endpoint } }),
};
