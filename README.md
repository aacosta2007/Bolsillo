# Bolsillo

App web personal para llevar tus finanzas: ingresos, gastos, cuentas (bolsillos), presupuestos, gastos recurrentes,
metas de ahorro y un dashboard. Pensada para el celular (PWA) y desplegada en tu propio servidor con Docker,
accesible desde cualquier lugar a través de Tailscale.

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 async · Alembic · arquitectura por capas (`backend/app/{domain,application,infrastructure,api}`) |
| Base de datos | MariaDB 11.4 LTS |
| Frontend | React 18 · Vite · TypeScript · Tailwind · TanStack Query · Recharts · PWA |
| Infra | Docker Compose · Caddy (sirve el front y hace proxy de `/api`) · backup diario con `mariadb-dump` |

Documentación: [contrato de API](docs/API.md) · [guía de diseño](docs/design/DESIGN.md) ·
[diseño en Claude Design](https://claude.ai/artifact/7UTsH9S86jJ6DXC2ZfTjUP)

## Desarrollo local

```bash
cp .env.example .env            # y edita los valores (COOKIE_SECURE=false en local)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
cd backend && python -m venv .venv && . .venv/Scripts/activate && pip install -e ".[dev]" && alembic upgrade head && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxy /api → :8000)
```

O todo en Docker: `docker compose up -d --build` → http://localhost:8080

## Despliegue en el servidor (Docker + Tailscale)

1. En el servidor: instala Docker y Tailscale (`tailscale up`) y clona el repo.
2. `cp .env.example .env` y cambia **todas** las claves y `JWT_SECRET`
   (`python3 -c "import secrets; print(secrets.token_urlsafe(64))"`). Deja `BIND_IP=127.0.0.1` y `COOKIE_SECURE=true`.
3. `docker compose up -d --build`
4. Publica la app solo dentro de tu tailnet con HTTPS:
   ```bash
   sudo tailscale serve --bg --https=443 http://127.0.0.1:8080
   ```
   Quedará en `https://<nombre-servidor>.<tu-tailnet>.ts.net` (activa MagicDNS y HTTPS en el panel de Tailscale).
   HTTPS es necesario para instalar la PWA y para la cookie segura de sesión.
5. Desde el celular con Tailscale activo, abre la URL → menú del navegador → **Agregar a pantalla de inicio**.

Alternativa sin `tailscale serve`: pon `BIND_IP=<tailscale ip -4>` y `COOKIE_SECURE=false`, y entra por `http://100.x.y.z:8080`
(funciona, pero sin instalación PWA ni cookie segura).

## Backups

El servicio `backup` genera `backups/bolsillo_YYYYMMDD_HHMMSS.sql.gz` al arrancar y cada día a las 03:00, y borra los
de más de `BACKUP_KEEP_DAYS` días. Restaurar:

```bash
gunzip -c backups/bolsillo_XXXX.sql.gz | docker compose exec -T db sh -c 'mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE"'
```

## Usuario

Al primer arranque se crea el usuario de `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD` si no existe ninguno.
También: `docker compose exec api python -m app.cli create-user --email tu@correo.com --password '...'`
