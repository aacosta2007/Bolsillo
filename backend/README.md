# Bolsillo — backend

FastAPI + SQLAlchemy 2.0 async (asyncmy) sobre MariaDB 11.4. Contrato: `../docs/API.md`.

## Capas

```
api  ->  application  ->  domain  <-  infrastructure
```

- `app/domain`: entidades, enums, excepciones, reglas puras (`rules.py`), interfaces de repositorio (`repositories.py`) y datos por defecto (`defaults.py`).
- `app/application`: casos de uso por módulo. Dependen solo de `domain`.
- `app/infrastructure`: ORM, repositorios SQL, Unit of Work, seguridad (argon2/JWT), scheduler, rate limit.
- `app/api`: routers `/api/v1`, schemas, dependencias y manejo de errores.
- `app/main.py`: composition root (lifespan: usuario inicial, recurrentes pendientes, scheduler 00:05).

## Variables de entorno

`DATABASE_URL` (`mysql+asyncmy://user:pass@host:3306/db?charset=utf8mb4`), `JWT_SECRET`, `ACCESS_TOKEN_MINUTES`,
`REFRESH_TOKEN_DAYS`, `COOKIE_SECURE`, `DEFAULT_TIMEZONE`, `DEFAULT_CURRENCY`, `INITIAL_USER_EMAIL`,
`INITIAL_USER_PASSWORD`, `CORS_ORIGINS` (coma-separado, vacío por defecto; p. ej. `http://localhost:5173`).

## Ejecutar

```bash
alembic upgrade head
uvicorn app.main:app --reload          # docs en /api/v1/docs
python -m app.cli create-user --email a@b.co --password "clave-larga-123"
```

## Tests

Requiere una MariaDB de pruebas:

```bash
docker run -d --name bolsillo-test-db -e MARIADB_ROOT_PASSWORD=test -e MARIADB_DATABASE=bolsillo_test \
  -e MARIADB_USER=test -e MARIADB_PASSWORD=test -p 127.0.0.1:53306:3306 mariadb:11.4 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --default-time-zone=+00:00
pip install -r requirements-dev.txt
pytest                      # unit (repos fake) + integración (API contra MariaDB)
pytest tests/unit           # solo unitarios, sin BD
docker rm -f bolsillo-test-db
```

La URL por defecto de tests es `mysql+asyncmy://test:test@127.0.0.1:53306/bolsillo_test`; se puede cambiar con `DATABASE_URL`.
Los tests de integración recrean el esquema con Alembic (downgrade base + upgrade head) y truncan las tablas entre tests.
