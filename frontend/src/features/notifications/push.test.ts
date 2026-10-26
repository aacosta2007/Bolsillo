import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({
  notificationsApi: {
    vapidPublicKey: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
  },
}));

import { notificationsApi } from './api';
import { ApiError } from '@/shared/api/client';
import { derivePushStatus, detectDevice, disablePush, enablePush, isServerWithoutKeys, resyncPush, urlBase64ToUint8Array } from './push';

const api = vi.mocked(notificationsApi);

describe('urlBase64ToUint8Array', () => {
  it('convierte base64url (con - y _ y sin padding) a bytes', () => {
    // bytes 0xfb 0xff 0xfe -> base64 "+//+" -> base64url "-__-"
    expect(Array.from(urlBase64ToUint8Array('-__-'))).toEqual([0xfb, 0xff, 0xfe]);
    expect(Array.from(urlBase64ToUint8Array('AQI'))).toEqual([1, 2]);
    expect(Array.from(urlBase64ToUint8Array('AQ'))).toEqual([1]);
  });
  it('una clave VAPID de 65 bytes mantiene su longitud', () => {
    const bytes = new Uint8Array(65).map((_, i) => (i * 7) % 256);
    const b64 = btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    expect(Array.from(urlBase64ToUint8Array(b64))).toEqual(Array.from(bytes));
  });
});

describe('derivePushStatus', () => {
  const base = { supported: true, permission: 'default' as NotificationPermission, hasSubscription: false, serverUnavailable: false };
  it('no soportado', () => expect(derivePushStatus({ ...base, supported: false, permission: 'unsupported' })).toBe('unsupported'));
  it('permiso denegado', () => expect(derivePushStatus({ ...base, permission: 'denied' })).toBe('denied'));
  it('servidor sin claves', () => expect(derivePushStatus({ ...base, serverUnavailable: true })).toBe('unavailable'));
  it('inactivo: sin permiso, o con permiso pero sin suscripción', () => {
    expect(derivePushStatus(base)).toBe('inactive');
    expect(derivePushStatus({ ...base, permission: 'granted' })).toBe('inactive');
  });
  it('activo: permiso concedido y suscripción local', () =>
    expect(derivePushStatus({ ...base, permission: 'granted', hasSubscription: true })).toBe('active'));
  it('denegado tiene prioridad sobre servidor sin claves', () =>
    expect(derivePushStatus({ ...base, permission: 'denied', serverUnavailable: true })).toBe('denied'));
});

describe('detectDevice / isServerWithoutKeys', () => {
  it('nombra el dispositivo', () => {
    expect(detectDevice('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36')).toBe('Android Chrome');
    expect(detectDevice('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1')).toBe('iOS Safari');
  });
  it('503 es "servidor sin claves"', () => {
    expect(isServerWithoutKeys(new ApiError(503, 'x'))).toBe(true);
    expect(isServerWithoutKeys(new ApiError(500, 'x'))).toBe(false);
    expect(isServerWithoutKeys(new Error('x'))).toBe(false);
  });
});

// ---- Mocks de navigator / Notification / PushManager ----
function fakeSub(endpoint = 'https://push.example/abc') {
  return {
    endpoint,
    toJSON: () => ({ endpoint, keys: { p256dh: 'P', auth: 'A' } }),
    unsubscribe: vi.fn().mockResolvedValue(true),
  };
}

function setupBrowser(opts: { permission: NotificationPermission; request?: NotificationPermission; existing?: ReturnType<typeof fakeSub> | null }) {
  const created = fakeSub('https://push.example/new');
  const pushManager = {
    getSubscription: vi.fn().mockResolvedValue(opts.existing ?? null),
    subscribe: vi.fn().mockResolvedValue(created),
  };
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: { ready: Promise.resolve({ pushManager }) } });
  (window as unknown as { PushManager: unknown }).PushManager = class {};
  const N = { permission: opts.permission, requestPermission: vi.fn().mockResolvedValue(opts.request ?? opts.permission) };
  (globalThis as unknown as { Notification: unknown }).Notification = N;
  return { pushManager, N, created };
}

describe('flujos de suscripción', () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => {
    delete (navigator as unknown as Record<string, unknown>).serviceWorker;
    delete (window as unknown as Record<string, unknown>).PushManager;
    delete (globalThis as unknown as Record<string, unknown>).Notification;
  });

  it('enablePush: pide permiso, suscribe con la clave y registra en el servidor', async () => {
    api.vapidPublicKey.mockResolvedValue({ public_key: 'AQI' });
    const { pushManager, N } = setupBrowser({ permission: 'default', request: 'granted' });
    await expect(enablePush()).resolves.toBe('active');
    expect(N.requestPermission).toHaveBeenCalledOnce();
    const arg = pushManager.subscribe.mock.calls[0]![0];
    expect(arg.userVisibleOnly).toBe(true);
    expect(Array.from(arg.applicationServerKey as Uint8Array)).toEqual([1, 2]);
    expect(api.subscribe).toHaveBeenCalledWith({ endpoint: 'https://push.example/new', keys: { p256dh: 'P', auth: 'A' }, device: expect.any(String) });
  });

  it('enablePush: permiso denegado no suscribe ni llama al servidor', async () => {
    api.vapidPublicKey.mockResolvedValue({ public_key: 'AQI' });
    const { pushManager } = setupBrowser({ permission: 'default', request: 'denied' });
    await expect(enablePush()).resolves.toBe('denied');
    expect(pushManager.subscribe).not.toHaveBeenCalled();
    expect(api.subscribe).not.toHaveBeenCalled();
  });

  it('enablePush: servidor sin claves (503) falla antes de pedir permiso', async () => {
    api.vapidPublicKey.mockRejectedValue(new ApiError(503, 'sin claves'));
    const { N } = setupBrowser({ permission: 'default' });
    await expect(enablePush()).rejects.toMatchObject({ status: 503 });
    expect(N.requestPermission).not.toHaveBeenCalled();
  });

  it('disablePush: cancela la suscripción local y la borra en el servidor', async () => {
    const existing = fakeSub();
    setupBrowser({ permission: 'granted', existing });
    await disablePush();
    expect(existing.unsubscribe).toHaveBeenCalled();
    expect(api.unsubscribe).toHaveBeenCalledWith('https://push.example/abc');
  });

  it('resyncPush: con permiso y suscripción local la re-registra (upsert)', async () => {
    setupBrowser({ permission: 'granted', existing: fakeSub() });
    await resyncPush();
    expect(api.subscribe).toHaveBeenCalledWith(expect.objectContaining({ endpoint: 'https://push.example/abc' }));
  });

  it('resyncPush: sin permiso o sin suscripción no hace nada, y nunca lanza', async () => {
    setupBrowser({ permission: 'default', existing: fakeSub() });
    await resyncPush();
    setupBrowser({ permission: 'granted', existing: null });
    await resyncPush();
    expect(api.subscribe).not.toHaveBeenCalled();
    setupBrowser({ permission: 'granted', existing: fakeSub() });
    api.subscribe.mockRejectedValueOnce(new Error('boom'));
    await expect(resyncPush()).resolves.toBeUndefined();
  });

  it('resyncPush: navegador sin soporte no hace nada', async () => {
    await resyncPush();
    expect(api.subscribe).not.toHaveBeenCalled();
  });
});
