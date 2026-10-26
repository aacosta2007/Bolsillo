import { ApiError } from '@/shared/api/client';
import { notificationsApi } from './api';

export type PushStatus = 'unsupported' | 'denied' | 'unavailable' | 'inactive' | 'active';

/** base64url (clave VAPID) → bytes para `applicationServerKey`. */
export function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  const raw = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export function isPushSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serviceWorker' in navigator && typeof window !== 'undefined' && 'PushManager' in window && 'Notification' in window;
}

export function currentPermission(): NotificationPermission | 'unsupported' {
  return typeof Notification === 'undefined' ? 'unsupported' : Notification.permission;
}

/** Estado que se muestra en el banner. Prioridad: soporte > permiso denegado > servidor sin claves > activo/inactivo. */
export function derivePushStatus(input: {
  supported: boolean;
  permission: NotificationPermission | 'unsupported';
  hasSubscription: boolean;
  serverUnavailable: boolean;
}): PushStatus {
  if (!input.supported) return 'unsupported';
  if (input.permission === 'denied') return 'denied';
  if (input.serverUnavailable) return 'unavailable';
  return input.permission === 'granted' && input.hasSubscription ? 'active' : 'inactive';
}

export const isServerWithoutKeys = (err: unknown) => err instanceof ApiError && err.status === 503;

/** Nombre del dispositivo para mostrarlo en el servidor, p. ej. "Android Chrome". */
export function detectDevice(ua: string = typeof navigator === 'undefined' ? '' : navigator.userAgent): string {
  const os = /Android/i.test(ua) ? 'Android' : /iPhone|iPad|iPod/i.test(ua) ? 'iOS' : /Windows/i.test(ua) ? 'Windows' : /Mac OS X/i.test(ua) ? 'Mac' : /Linux/i.test(ua) ? 'Linux' : 'Dispositivo';
  const browser = /Edg\//.test(ua) ? 'Edge' : /Firefox\//.test(ua) ? 'Firefox' : /Chrome\/|CriOS/.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : '';
  return `${os} ${browser}`.trim();
}

/** `serviceWorker.ready` nunca resuelve si no hay SW registrado (p. ej. navegadores embebidos): se limita la espera. */
async function registration(timeoutMs = 5000): Promise<ServiceWorkerRegistration> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () => reject(new Error('La app aún no terminó de instalarse en este navegador. Recarga la página e intenta de nuevo.')),
      timeoutMs,
    );
  });
  try {
    return await Promise.race([navigator.serviceWorker.ready, timeout]);
  } finally {
    clearTimeout(timer);
  }
}

export async function getLocalSubscription(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null;
  const reg = await registration();
  return reg.pushManager.getSubscription();
}

function toInput(sub: PushSubscription) {
  const json = sub.toJSON();
  return {
    endpoint: sub.endpoint,
    keys: { p256dh: json.keys?.p256dh ?? '', auth: json.keys?.auth ?? '' },
    device: detectDevice(),
  };
}

export type EnableResult = 'active' | 'denied' | 'dismissed';

/** Debe llamarse desde un toque del usuario: pide permiso, suscribe y registra en el servidor. */
export async function enablePush(): Promise<EnableResult> {
  // Si el servidor no tiene claves lanza ApiError 503 antes de molestar al usuario con el permiso.
  const { public_key } = await notificationsApi.vapidPublicKey();
  const permission = await Notification.requestPermission();
  if (permission === 'denied') return 'denied';
  if (permission !== 'granted') return 'dismissed';
  const reg = await registration();
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(public_key) }));
  await notificationsApi.subscribe(toInput(sub));
  return 'active';
}

/** Cancela la suscripción local y la borra del servidor. */
export async function disablePush(): Promise<void> {
  const sub = await getLocalSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  await sub.unsubscribe();
  await notificationsApi.unsubscribe(endpoint);
}

/** Al iniciar sesión: si ya hay suscripción local y permiso, la re-registra (upsert) sin avisar. */
export async function resyncPush(): Promise<void> {
  try {
    if (!isPushSupported() || Notification.permission !== 'granted') return;
    const sub = await getLocalSubscription();
    if (sub) await notificationsApi.subscribe(toInput(sub));
  } catch {
    /* silencioso: la bandeja funciona igual */
  }
}
