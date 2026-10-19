# Bolsillo — frontend

PWA mobile-first (React 18 + Vite + TypeScript + Tailwind + TanStack Query).

## Comandos
- `npm ci` instala dependencias
- `npm run dev` servidor en :5173 con proxy `/api` -> `http://localhost:8000`
- `npm run build` typecheck + build de producción (genera PWA/service worker)
- `npm run lint` · `npm test`
- `node scripts/gen-icons.mjs` regenera los iconos PNG de la PWA

## Docker
Desde la raíz del repo: `docker build -t bolsillo-web ./frontend`.
Caddy sirve `/srv`, hace proxy de `/api/*` a `api:8000` y aplica fallback SPA.

## Estructura
`src/app` (router, providers, layout) · `src/shared` (api, lib, ui) · `src/features/*` (api, hooks, types, components, pages).
El contrato de API está en `docs/API.md`. El access token vive solo en memoria; el refresh usa cookie httpOnly.
