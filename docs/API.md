# Bolsillo — Contrato de API v1

Este documento es la **fuente de verdad** compartida entre backend y frontend. Cualquier cambio debe hacerse aquí primero.

## Convenciones generales

- Base de datos: **MariaDB 11.4 LTS** (utf8mb4, InnoDB, fechas-hora guardadas en UTC).

- Prefijo: `/api/v1`. JSON en `snake_case`.
- IDs: UUID v4 como string.
- **Dinero**: siempre `string` decimal con 2 decimales en las respuestas (`"125000.00"`). Las peticiones aceptan string o número. Nunca float en BD (`DECIMAL(14,2)` en MariaDB). Montos siempre **positivos**; el signo lo da `type`.
- Fechas: `"YYYY-MM-DD"`. Fecha-hora: ISO 8601 UTC (`"2026-10-18T14:03:00Z"`). Mes: `"YYYY-MM"` en query params.
- Zona horaria del usuario por defecto `America/Bogota`; moneda por defecto `COP`.
- Errores: `{"detail": "mensaje legible en español"}` con 400/401/403/404/409. Validación: 422 (formato estándar de FastAPI).
- Todas las rutas excepto `/health`, `/auth/login` y `/auth/refresh` requieren `Authorization: Bearer <access_token>`.
- Todo recurso pertenece a un `user_id`; el backend filtra siempre por el usuario autenticado (acceder a recurso ajeno → 404).
- Listas paginadas: `{"items": [...], "total": 120, "page": 1, "page_size": 50}`.

## Salud
`GET /health` → `200 {"status": "ok"}`

## Auth
| Método | Ruta | Body | Respuesta |
|---|---|---|---|
| POST | `/auth/login` | `{"email","password"}` | `200 TokenResponse` + cookie `refresh_token` (httpOnly, SameSite=Strict, Path=`/api/v1/auth`, Secure si `COOKIE_SECURE=true`) |
| POST | `/auth/refresh` | — (usa cookie) | `200 TokenResponse` (rota la cookie) / `401` |
| POST | `/auth/logout` | — | `204`, borra cookie |
| GET | `/auth/me` | — | `200 User` |
| PATCH | `/auth/me` | `{"currency"?, "timezone"?, "display_name"?}` | `200 User` |
| POST | `/auth/change-password` | `{"current_password","new_password"}` | `204` / `400` |

```json
TokenResponse = {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 900}
User = {"id": "uuid", "email": "a@b.co", "display_name": "Andrés", "currency": "COP", "timezone": "America/Bogota", "created_at": "..."}
```
Access token: 15 min. Refresh token: 30 días. El frontend guarda el access token **en memoria**; ante un 401 llama una vez a `/auth/refresh` y reintenta.
Rate limit simple en login: 5 intentos fallidos / 5 min por IP → `429`.

## Cuentas (bolsillos)
`GET /accounts?include_archived=false` → `Account[]`
`POST /accounts` · `GET /accounts/{id}` · `PATCH /accounts/{id}` · `DELETE /accounts/{id}` (`409` si tiene movimientos; en ese caso archivar con PATCH)

```json
Account = {
  "id": "uuid", "name": "Bancolombia", "type": "cash|bank|credit_card|savings|wallet",
  "initial_balance": "0.00", "color": "#2563eb", "icon": "landmark", "archived": false,
  "balance": "1250000.00", "created_at": "..."
}
AccountCreate = {"name", "type", "initial_balance"?: "0", "color"?, "icon"?}
```
`balance` es calculado: `initial_balance + ingresos − gastos − transferencias salientes + transferencias entrantes`.

## Categorías
`GET /categories?kind=income|expense` → `Category[]`
`POST /categories` · `PATCH /categories/{id}` · `DELETE /categories/{id}` (`409` si tiene movimientos o presupuestos)

```json
Category = {"id": "uuid", "name": "Comida", "kind": "income|expense", "icon": "utensils", "color": "#f97316", "parent_id": null}
```
`icon` es un nombre de icono de **lucide** (kebab-case). Al crear un usuario se siembran categorías por defecto:
- Gasto: Comida (`utensils`), Transporte (`bus`), Hogar/Arriendo (`home`), Servicios (`zap`), Salud (`heart-pulse`), Entretenimiento (`clapperboard`), Compras (`shopping-bag`), Educación (`graduation-cap`), Suscripciones (`repeat`), Otros (`circle-ellipsis`).
- Ingreso: Salario (`briefcase`), Freelance (`laptop`), Inversiones (`trending-up`), Regalos (`gift`), Otros ingresos (`plus-circle`).

## Movimientos (transacciones)
`GET /transactions?from=&to=&account_id=&category_id=&type=&q=&page=1&page_size=50` → `Page<Transaction>` ordenado por `date desc, created_at desc`. `q` busca en `note` (LIKE, collation utf8mb4_unicode_ci ya es case-insensitive).
`POST /transactions` · `GET /transactions/{id}` · `PATCH /transactions/{id}` · `DELETE /transactions/{id}` (204)

```json
Transaction = {
  "id": "uuid", "type": "income|expense|transfer", "amount": "45000.00", "date": "2026-10-18",
  "account_id": "uuid", "category_id": "uuid|null", "transfer_account_id": "uuid|null",
  "note": "Almuerzo", "recurring_id": "uuid|null", "created_at": "..."
}
TransactionCreate = {"type", "amount", "date", "account_id", "category_id"?, "transfer_account_id"?, "note"?}
```
Reglas de negocio (devuelven 400):
- `income`/`expense`: `category_id` obligatorio y su `kind` debe coincidir con `type`; `transfer_account_id` debe ser null.
- `transfer`: `transfer_account_id` obligatorio y distinto de `account_id`; `category_id` debe ser null.
- `amount > 0`. Cuentas archivadas no aceptan movimientos nuevos.

## Presupuestos
`GET /budgets?month=YYYY-MM` → `BudgetStatus[]`
`POST /budgets` · `PATCH /budgets/{id}` · `DELETE /budgets/{id}`
`POST /budgets/copy` body `{"from_month":"YYYY-MM","to_month":"YYYY-MM"}` → `BudgetStatus[]` (omite los que ya existen)

```json
BudgetStatus = {
  "id": "uuid", "category_id": "uuid", "month": "2026-10", "amount_limit": "600000.00",
  "alert_threshold": "0.80", "spent": "510000.00", "remaining": "90000.00",
  "percent": 85.0, "status": "ok|warning|exceeded"
}
BudgetCreate = {"category_id", "month": "YYYY-MM", "amount_limit", "alert_threshold"?: 0.8}
```
Solo categorías de gasto. Único por (usuario, categoría, mes) → `409`. `status`: `exceeded` si spent > limit, `warning` si percent ≥ threshold·100, si no `ok`.

## Recurrentes
`GET /recurring` → `RecurringRule[]` · `POST /recurring` · `PATCH /recurring/{id}` · `DELETE /recurring/{id}`
`POST /recurring/run` → `{"created": 3}` (genera todos los movimientos pendientes hasta hoy; idempotente)
`GET /recurring/upcoming?days=30` → `UpcomingItem[]` ordenado por fecha

```json
RecurringRule = {
  "id": "uuid", "type": "income|expense", "amount": "39900.00", "account_id": "uuid", "category_id": "uuid",
  "note": "Netflix", "frequency": "daily|weekly|monthly|yearly|monthly_days", "interval": 1,
  "days_of_month": null, "weekend_adjust": "none", "is_paycheck": false,
  "start_date": "2026-01-05", "end_date": null, "next_run_date": "2026-11-05", "active": true,
  "monthly_equivalent": "39900.00"
}
UpcomingItem = {"rule_id": "uuid", "date": "2026-11-05", "type": "expense", "amount": "39900.00", "category_id": "uuid", "account_id": "uuid", "note": "Netflix", "is_paycheck": false}
```
Al crear, `next_run_date` = primera ocurrencia ≥ `start_date` (para las frecuencias clásicas es `start_date`). El job diario (00:05 hora del usuario, y también al arrancar) crea un movimiento por cada ocurrencia con fecha efectiva `<= hoy`, enlazado con `recurring_id`, y avanza `next_run_date` en la misma transacción de BD. Mensual en día 31 → último día del mes.

### Frecuencia `monthly_days` (quincenal y días fijos)
- `days_of_month`: obligatorio si `frequency = monthly_days` (si no, debe ser `null`). String con 1 a 3 valores separados por coma, sin repetir, ordenados al guardar: números `1`–`31` o `L` (= último día del mes). Ej.: `"15,L"` (quincena: 15 y último día), `"15,30"`, `"5"`. Inválido → 422.
- `interval` se ignora (se guarda `1`). Monto = **por ocurrencia** (sueldo de 2.000.000/mes con `"15,L"` → `amount = "1000000"`).
- Un día que no existe en el mes se ajusta al último día real: `30` en febrero → 28/29; `31` en abril → 30. Si dos valores caen en la misma fecha ajustada (p. ej. `"30,L"` en febrero) se genera **una sola** ocurrencia.
- `weekend_adjust`: `none` (defecto) | `previous_business_day` → si la fecha cae sábado o domingo, el movimiento se fecha el viernes anterior. Aplica a todas las frecuencias. `next_run_date` guarda la fecha **nominal** (sin ajuste) para no duplicar ni saltar; `UpcomingItem.date` y el movimiento usan la fecha **efectiva** (ajustada), y el job genera cuando la fecha efectiva `<= hoy`.
- `is_paycheck`: solo permitido en `type = income` (si no → 400). Marca la regla como "mi sueldo"; se usará para calcular las quincenas de pago. Puede haber varias reglas marcadas.
- `monthly_equivalent` (solo lectura): equivalente mensual aproximado del monto (`monthly_days`: amount × cantidad de días; `monthly`: amount / interval; `weekly`: amount × 52/12/interval; `daily`: amount × 365/12/interval; `yearly`: amount / 12 / interval), redondeado a 2 decimales. Lo usa la UI para "≈ $ 2.000.000 al mes" y "Fijos al mes".
- Cambiar `frequency`, `days_of_month`, `interval`, `start_date` o `weekend_adjust` recalcula `next_run_date` como la primera ocurrencia nominal > hoy (no regenera el pasado), igual que hoy.

## Metas de ahorro
`GET /goals` → `Goal[]` · `POST /goals` · `PATCH /goals/{id}` · `DELETE /goals/{id}`
`GET /goals/{id}/contributions` → `Contribution[]` · `POST /goals/{id}/contributions` · `DELETE /goals/{id}/contributions/{cid}`

```json
Goal = {
  "id": "uuid", "name": "Viaje a Cartagena", "target_amount": "3000000.00", "target_date": "2027-06-01|null",
  "account_id": "uuid|null", "color": "#10b981", "icon": "plane", "saved": "750000.00", "percent": 25.0,
  "monthly_needed": "375000.00|null", "completed": false, "created_at": "..."
}
Contribution = {"id": "uuid", "goal_id": "uuid", "amount": "250000.00", "date": "2026-10-01", "note": null}
```
`monthly_needed` = (target − saved) / meses restantes hasta `target_date` (mín. 1), null si no hay fecha o ya se completó. Los aportes pueden ser negativos (retiros) pero `saved` no puede quedar < 0 → 400.

## Dashboard
`GET /dashboard/summary?from=YYYY-MM-DD&to=YYYY-MM-DD` (por defecto: mes actual)

```json
{
  "period": {"from": "2026-10-01", "to": "2026-10-31"},
  "total_balance": "4200000.00",
  "income": "3500000.00", "expense": "2100000.00", "net": "1400000.00", "savings_rate": 40.0,
  "by_category": [{"category_id": "uuid", "name": "Comida", "color": "#f97316", "icon": "utensils", "total": "600000.00", "percent": 28.6}],
  "monthly_trend": [{"month": "2026-05", "income": "3400000.00", "expense": "2500000.00"}],
  "accounts": [Account],
  "budgets_at_risk": [BudgetStatus],
  "upcoming_recurring": [UpcomingItem],
  "recent_transactions": [Transaction],
  "current_pay_period": PayPeriod | null,
  "previous_pay_period": PayPeriod | null,
  "next_payday": {"date": "2026-10-30", "amount": "1000000.00", "note": "Sueldo"} | null
}
```
- `current_pay_period` / `previous_pay_period`: quincena de pago que contiene **hoy** y la anterior (ver "Quincenas de pago"); no dependen de `from`/`to`. `next_payday`: siguiente fecha de pago efectiva > hoy (suma de montos si varias reglas de sueldo caen el mismo día; `note` de la primera); null si no hay sueldo marcado.
- `by_category`: solo gastos del periodo, ordenado desc, `percent` sobre el total de gastos.
- `monthly_trend`: últimos 6 meses terminando en el mes de `to` (meses sin datos con `"0.00"`).
- `budgets_at_risk`: presupuestos del mes de `to` con status `warning` o `exceeded`.
- `upcoming_recurring`: próximos 7 días. `recent_transactions`: últimos 5.
- Las transferencias no cuentan como ingreso ni gasto.

## Reportes
`GET /reports/by-category?from&to&type=expense|income` → `[{category_id, name, color, icon, total, percent, count}]`
`GET /reports/monthly-trend?months=12` → `[{month, income, expense, net}]`

### Quincenas de pago
`GET /reports/pay-periods?count=6` → `PayPeriod[]` (1–24, defecto 6), de la **más reciente a la más antigua**; la primera es la que contiene hoy (`in_progress = true`).

```json
PayPeriod = {
  "start": "2026-10-15", "end": "2026-10-29", "days": 15, "days_elapsed": 6, "days_remaining": 10,
  "in_progress": true, "source": "paycheck|calendar",
  "income": "1350000.00", "expense": "612400.00", "net": "737600.00",
  "spent_per_day": "102066.67",
  "available_per_day": "73760.00",
  "spent_percent": 45.4, "time_percent": 40.0,
  "status": "en_curso|ahorro|justo|deficit",
  "by_category": [{"category_id": "uuid", "name": "Comida", "color": "#f97316", "icon": "utensils", "total": "210000.00", "percent": 34.3}]
}
```
**Definición de periodo**
- Fechas de pago = unión (sin duplicados) de las fechas **efectivas** de todas las reglas recurrentes activas con `is_paycheck = true`, calculadas desde su calendario (desde `start_date`, respetando `end_date`), no desde los movimientos. Así los periodos no cambian si un pago se registró tarde o a mano.
- Un periodo va de una fecha de pago hasta el día anterior a la siguiente (`end = siguiente_pago − 1 día`). Ej.: pagos 15 oct y 30 oct → periodo 15–29 oct. Antes del primer pago de la primera regla no hay periodos de sueldo.
- Sin reglas de sueldo (o antes del primer pago) → **respaldo de calendario** (`source = "calendar"`): 1–15 y 16–fin de mes.
- `income` / `expense`: movimientos con `date` en `[start, end]`; las transferencias no cuentan. `net = income − expense`.
- `days_elapsed` = días desde `start` hasta hoy inclusive (solo en curso; si no, = `days`). `days_remaining` = `days − days_elapsed` + 1 si en curso (incluye hoy), 0 si cerrado.
- `spent_per_day` = `expense / days_elapsed`. `available_per_day` (solo en curso, si no null) = `max(net, 0) / days_remaining`.
- `spent_percent` = expense/income×100 (0 si income = 0); `time_percent` = days_elapsed/days×100. Ambos con 1 decimal.
- `status`: en curso → `en_curso`; `net < 0` → `deficit`; `income = 0` o `net < 10 % de income` → `justo`; si no → `ahorro`. Si una regla de sueldo terminó (`end_date`) y no hay pago siguiente, el periodo en curso cierra el 15 o el fin de mes, lo que llegue primero.
- `by_category`: gastos del periodo agrupados (igual que en dashboard).

## Exportar
`GET /export/csv?from&to` → `text/csv; charset=utf-8` con BOM, separador `,`, columnas:
`fecha,tipo,monto,cuenta,categoria,cuenta_destino,nota`. Header `Content-Disposition: attachment; filename="bolsillo_<from>_<to>.csv"`.
