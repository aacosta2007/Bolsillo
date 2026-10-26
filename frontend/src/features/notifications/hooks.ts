import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from './api';
import type { NotificationPreferences, NotificationsPage } from './types';

const KEY = ['notifications'] as const;

/** Bandeja (más recientes primero) con `unread_count`. */
export const useNotifications = (pageSize = 30) =>
  useQuery({ queryKey: [...KEY, 'list', pageSize], queryFn: () => notificationsApi.list(pageSize) });

/** Contador de no leídas para la campana: se refresca al enfocar la ventana. */
export const useUnreadCount = (enabled = true) =>
  useQuery({
    queryKey: [...KEY, 'unread'],
    queryFn: () => notificationsApi.list(1, true),
    select: (d: NotificationsPage) => d.unread_count,
    enabled,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export const usePreferences = () => useQuery({ queryKey: [...KEY, 'preferences'], queryFn: notificationsApi.preferences });

/** PATCH con actualización optimista; revierte si falla. */
export function useUpdatePreferences() {
  const qc = useQueryClient();
  const key = [...KEY, 'preferences'];
  return useMutation({
    mutationFn: (patch: Partial<NotificationPreferences>) => notificationsApi.updatePreferences(patch),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<NotificationPreferences>(key);
      if (prev) qc.setQueryData<NotificationPreferences>(key, { ...prev, ...patch });
      return { prev };
    },
    onError: (_e, _p, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
    },
    onSuccess: (data) => qc.setQueryData(key, data),
  });
}

export function useSendTest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.sendTest(),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
