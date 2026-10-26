/// <reference lib="webworker" />
// Service worker propio (vite-plugin-pwa, strategies: 'injectManifest').
// Conserva el comportamiento del SW generado antes (generateSW + autoUpdate):
//  - precache de los assets del build (self.__WB_MANIFEST) y limpieza de cachés viejos
//  - skipWaiting + clientsClaim: una versión nueva toma el control sin esperar
//  - navegación SPA: cualquier navegación (excepto /api/) sirve /index.html del precache
// y añade Web Push (evento `push`) y apertura al tocar el aviso (`notificationclick`).
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching';
import { clientsClaim } from 'workbox-core';
import { NavigationRoute, registerRoute } from 'workbox-routing';

declare const self: ServiceWorkerGlobalScope;

self.skipWaiting();
clientsClaim();

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html'), { denylist: [/^\/api\//] }));

interface PushPayload {
  title?: string;
  body?: string;
  url?: string;
  tag?: string;
  notification_id?: string;
}

const ICON = '/icons/icon-192.png';

self.addEventListener('push', (event) => {
  let payload: PushPayload = {};
  try {
    payload = (event.data?.json() as PushPayload | undefined) ?? {};
  } catch {
    payload = { body: event.data?.text() };
  }
  const title = payload.title || 'Bolsillo';
  event.waitUntil(
    self.registration.showNotification(title, {
      body: payload.body,
      icon: ICON,
      badge: ICON,
      tag: payload.tag,
      data: { url: payload.url || '/avisos', notification_id: payload.notification_id },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const data = (event.notification.data ?? {}) as { url?: string };
  const target = new URL(data.url || '/avisos', self.location.origin).href;

  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      const existing = windows.find((c) => new URL(c.url).origin === self.location.origin);
      if (existing) {
        try {
          const navigated = await existing.navigate(target);
          await (navigated ?? existing).focus();
          return;
        } catch {
          /* si no se puede navegar, abrimos una ventana nueva */
        }
      }
      await self.clients.openWindow(target);
    })(),
  );
});
