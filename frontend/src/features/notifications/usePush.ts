import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { notificationsApi } from './api';
import { currentPermission, derivePushStatus, disablePush, enablePush, getLocalSubscription, isPushSupported, isServerWithoutKeys, type PushStatus } from './push';
import { errorMessage } from '@/shared/ui';

export function usePush(): { status: PushStatus | 'loading'; busy: boolean; error: string | null; enable: () => Promise<void>; disable: () => Promise<void> } {
  const supported = isPushSupported();
  const [permission, setPermission] = useState(currentPermission());
  const [hasSub, setHasSub] = useState<boolean | null>(supported ? null : false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serverDown, setServerDown] = useState(false);

  const keyQuery = useQuery({
    queryKey: ['notifications', 'vapid'],
    queryFn: notificationsApi.vapidPublicKey,
    enabled: supported,
    retry: false,
    staleTime: 5 * 60_000,
  });

  const refresh = useCallback(async () => {
    setPermission(currentPermission());
    try {
      setHasSub(!!(await getLocalSubscription()));
    } catch {
      setHasSub(false);
    }
  }, []);

  useEffect(() => {
    if (supported) void refresh();
  }, [supported, refresh]);

  const unavailable = serverDown || isServerWithoutKeys(keyQuery.error);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      if (isServerWithoutKeys(e)) setServerDown(true);
      else setError(errorMessage(e));
    } finally {
      await refresh();
      setBusy(false);
    }
  };

  const status: PushStatus | 'loading' =
    supported && hasSub === null ? 'loading' : derivePushStatus({ supported, permission, hasSubscription: !!hasSub, serverUnavailable: unavailable });

  return {
    status,
    busy,
    error,
    enable: () => run(async () => void (await enablePush())),
    disable: () => run(disablePush),
  };
}
