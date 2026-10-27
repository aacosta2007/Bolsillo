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
  "income": "1350000.00", "salary_income": "1000000.00", "extra_income": "350000.00",
  "expense": "612400.00", "net": "737600.00",
  "spent_per_day": "102066.67",
  "available_per_day": "73760.00",
  "spent_percent": 45.4, "time_percent": 40.0,
  "status": "en_curso|ahorro|justo|deficit|calendario",
  "by_category": [{"category_id": "uuid", "name": "Comida", "color": "#f97316", "icon": "utensils", "total": "210000.00", "percent": 34.3}]
}
```
**Definición de periodo**
- **Ingreso de sueldo**: movimiento de ingreso generado por una regla con `is_paycheck = true` (`recurring_id`), **o** registrado a mano en la misma **categoría** que alguna regla de sueldo activa (p. ej. "Salario"). Las reglas de sueldo pueden empezar en el futuro: su categoría igual identifica los sueldos registrados a mano.
- Fechas de pago = **pasadas** (≤ hoy): las fechas de los ingresos de sueldo reales; **futuras** (> hoy): las fechas **efectivas** del calendario de las reglas de sueldo activas (desde `start_date`, respetando `end_date`). Se unen sin duplicados y, si dos fechas quedan a 3 días o menos, se conserva solo la primera (un ajuste o un bono no parten la quincena). Un pago programado que nunca llegó no crea periodo.
- `salary_income` = ingresos de sueldo del periodo; `extra_income` = `income − salary_income` (todo ingreso que no sea sueldo). `income`, `net` y las métricas usan el total.
- Un periodo va de una fecha de pago hasta el día anterior a la siguiente (`end = siguiente_pago − 1 día`). Ej.: pagos 15 oct y 30 oct → periodo 15–29 oct. Antes del primer pago de la primera regla no hay periodos de sueldo.
- Sin reglas de sueldo (o antes del primer ingreso de sueldo) → **respaldo de calendario** (`source = "calendar"`): 1–15 y 16–fin de mes.
- `income` / `expense`: movimientos con `date` en `[start, end]`; las transferencias no cuentan. `net = income − expense`.
- `days_elapsed` = días desde `start` hasta hoy inclusive (solo en curso; si no, = `days`). `days_remaining` = `days − days_elapsed` + 1 si en curso (incluye hoy), 0 si cerrado.
- `spent_per_day` = `expense / days_elapsed`. `available_per_day` (solo en curso, si no null) = `max(net, 0) / days_remaining`.
- `spent_percent` = expense/income×100 (0 si income = 0); `time_percent` = days_elapsed/days×100. Ambos con 1 decimal.
- `status`: en curso → `en_curso`; periodo cerrado con `source = "calendar"` → `calendario` (sin juicio: no se sabe cuánto es el sueldo); `net < 0` → `deficit`; `income = 0` o `net < 10 % de income` → `justo`; si no → `ahorro`. Si una regla de sueldo terminó (`end_date`) y no hay pago siguiente, el periodo en curso cierra el 15 o el fin de mes, lo que llegue primero.
- `by_category`: gastos del periodo agrupados (igual que en dashboard).

### Reporte mensual
`GET /reports/monthly/{YYYY-MM}` → `MonthlyReport` (JSON) · `GET /reports/monthly/{YYYY-MM}.pdf` → `application/pdf`
(`Content-Disposition: attachment; filename="bolsillo_reporte_YYYY-MM.pdf"`). Mes futuro → 400; formato inválido → 422.
Se puede pedir el mes en curso (parcial: `is_partial = true`). "Mes anterior" = el mes calendario previo.

```json
MonthlyReport = {
  "month": "2026-10", "is_partial": false, "generated_at": "2026-11-01T13:00:00Z", "currency": "COP",
  "summary": {
    "income": "2350000.00", "expense": "1684300.00", "net": "665700.00", "savings_rate": 28.3,
    "prev": {"income": "2000000.00", "expense": "1590000.00", "net": "410000.00", "savings_rate": 20.5},
    "income_change_pct": 17.5, "expense_change_pct": 5.9, "net_change_pct": 62.4
  },
  "expense_by_category": [{"category_id": "uuid", "name": "Comida", "color": "#0F5E55", "icon": "utensils",
     "total": "452300.00", "prev_total": "383300.00", "change_pct": 18.0, "percent": 26.9, "count": 14}],
  "income_by_category": [{"category_id": "uuid", "name": "Salario", "color": "#1D4ED8", "icon": "briefcase",
     "total": "2000000.00", "prev_total": "2000000.00", "change_pct": 0.0, "percent": 85.1, "count": 2, "is_new": false}],
  "top_expenses": [{"transaction_id": "uuid", "date": "2026-10-05", "note": "Arriendo", "category": "Hogar/Arriendo", "account": "Bancolombia", "amount": "700000.00"}],
  "daily": [{"date": "2026-10-01", "expense": "12000.00", "income": "0.00", "is_payday": false}],
  "daily_stats": {"max_day": "2026-10-05", "max_day_expense": "715000.00", "avg_daily_expense": "54332.26", "no_spend_days": 4},
  "pay_periods": [PayPeriod],
  "budgets": [BudgetStatus],
  "budgets_summary": {"ok": 3, "warning": 1, "exceeded": 1},
  "goals": [{"id": "uuid", "name": "Viaje a Cartagena", "color": "#0F5E55", "target_amount": "3000000.00", "saved": "1050000.00",
     "percent": 35.0, "contributed_this_month": "300000.00", "monthly_needed": "275000.00", "status": "on_track|behind|completed|no_target_date"}],
  "trend": [{"month": "2026-05", "income": "2000000.00", "expense": "1750000.00", "net": "250000.00", "savings_rate": 12.5}],
  "insights": [{"kind": "category_up|category_down|savings_record|new_income|budget_exceeded|pay_period_short|no_spend_days|savings_rate", "tone": "positive|warning|neutral", "text": "Gastaste 18 % más en Comida que en septiembre ($ 69.000 más)."}]
}
```
- Transferencias no cuentan como ingreso ni gasto. `change_pct` = (actual − anterior)/anterior × 100 con 1 decimal; `null` si anterior = 0 (en ingresos se marca `is_new = true` si anterior = 0 y actual > 0).
- `expense_by_category` incluye categorías con gasto en el mes **o** en el mes anterior (una que bajó a 0 aparece con `change_pct = -100`), ordenadas por `total` desc. `percent` sobre el total del mes.
- `top_expenses`: 5 gastos más grandes del mes. `daily`: un elemento por día del mes (hasta hoy si `is_partial`); `is_payday` si hay ingreso de una regla `is_paycheck` ese día. `avg_daily_expense` = gasto / días considerados.
- `pay_periods`: quincenas de pago (ver arriba) que **se cruzan** con el mes, en orden cronológico.
- `budgets`: presupuestos del mes con su estado. `goals`: metas con `contributed_this_month` (suma de aportes del mes); `status`: `completed` si saved ≥ target, `no_target_date` si no tiene fecha, `on_track` si contributed_this_month ≥ monthly_needed (o no se necesita), si no `behind`.
- `trend`: 6 meses terminando en `month`.
- `insights`: entre 2 y 6 observaciones **calculadas por reglas** (no IA), ordenadas por relevancia: categoría con mayor alza/baja (≥ 10 % y ≥ $ 20.000 de diferencia), récord de ahorro de los últimos 6 meses, ingreso nuevo, presupuestos excedidos, quincena más corta/larga o en déficit, días sin gasto, tasa de ahorro vs 20 %. Montos en pesos enteros con formato es-CO; nombres de mes en español.
- **PDF**: A4 vertical, 3 páginas como el diseño `docs/design/v2/PDF1–3.dc.html` (1: portada con resumen, observaciones, a dónde fue el dinero, quincenas del mes, tendencia; 2: gastos por categoría con dona y tabla vs mes anterior, top 5, ingresos por fuente, gasto día a día; 3: presupuestos, metas, tasa de ahorro 6 meses y "Para el próximo mes"). Pie con "Página N de 3". Gráficas en SVG vectorial. Fuentes Bricolage Grotesque + Figtree embebidas.

## Exportar
`GET /export/csv?from&to` → `text/csv; charset=utf-8` con BOM, separador `,`, columnas:
`fecha,tipo,monto,cuenta,categoria,cuenta_destino,nota`. Header `Content-Disposition: attachment; filename="bolsillo_<from>_<to>.csv"`.

## Notificaciones
Web Push estándar (VAPID). El servidor guarda cada aviso en la bandeja (`notifications`) y, si el usuario tiene suscripciones push y el tipo está activado, lo envía cifrado a cada dispositivo. La bandeja funciona aunque push falle o esté desactivado.

| Método | Ruta | Body | Respuesta |
|---|---|---|---|
| GET | `/notifications/vapid-public-key` | — | `200 {"public_key": "BL...base64url"}` (`503` si el servidor no tiene claves VAPID) |
| POST | `/notifications/subscriptions` | `{"endpoint", "keys": {"p256dh", "auth"}, "device"?: "Android Chrome"}` | `201 Subscription` (upsert por `endpoint`) |
| DELETE | `/notifications/subscriptions?endpoint=...` | — | `204` |
| GET | `/notifications?unread_only=false&page=1&page_size=30` | — | `200 Page<Notification> + "unread_count"` (más recientes primero) |
| POST | `/notifications/{id}/read` | — | `204` |
| POST | `/notifications/read-all` | — | `204` |
| GET | `/notifications/preferences` | — | `200 Preferences` |
| PATCH | `/notifications/preferences` | campos de `Preferences` | `200 Preferences` |
| POST | `/notifications/test` | — | `200 {"sent": 1, "failed": 0}` (crea un aviso de prueba y lo envía) |

```json
Notification = {"id": "uuid", "kind": "budget_warning|budget_exceeded|upcoming_recurring|payday|monthly_report|test",
  "title": "Comida llegó al 85 %", "body": "Te quedan $ 90.000 de tu presupuesto para 11 días.",
  "url": "/presupuestos", "read": false, "created_at": "..."}
Preferences = {"budget_alerts": true, "upcoming_alerts": true, "upcoming_days_before": 1, "payday_alerts": true,
  "monthly_report_alerts": true, "notify_hour": 8}
Subscription = {"id": "uuid", "endpoint": "https://fcm.googleapis.com/...", "device": "Android Chrome", "created_at": "..."}
```
- `upcoming_days_before`: 0–7 (0 = el mismo día). `notify_hour`: 0–23, hora local del usuario.
- **Payload push** (JSON cifrado): `{"title", "body", "url", "tag": "<kind>:<dedupe_key>", "notification_id"}`. El service worker muestra la notificación con icono de la app y al tocarla abre/enfoca `url`.
- **Deduplicación**: cada aviso tiene `dedupe_key` única por usuario; si ya existe no se crea ni se envía de nuevo.

**Disparadores**
| kind | Cuándo | dedupe_key | Texto (ejemplo) |
|---|---|---|---|
| `budget_warning` / `budget_exceeded` | Justo después de crear/editar un **gasto** (y en el job diario como respaldo) cuando un presupuesto del mes cruza el umbral o se excede | `budget:<budget_id>:<YYYY-MM>:<warning\|exceeded>` | "Comida llegó al 85 %" / "Entretenimiento excedido: te pasaste por $ 20.000" |
| `upcoming_recurring` | Job diario a `notify_hour`: ocurrencias de recurrentes activos (gasto **e** ingreso que no sea sueldo) con fecha efectiva = hoy + `upcoming_days_before` | `upcoming:<rule_id>:<fecha>` | "Mañana: Arriendo $ 1.200.000 desde Bancolombia" |
| `payday` | Cuando el job de recurrentes genera un movimiento de una regla `is_paycheck` | `payday:<rule_id>:<fecha>` | "Llegó tu quincena: $ 1.000.000. Puedes gastar ≈ $ 66.600 por día hasta el 29 oct" (usa `available_per_day` de la quincena actual) |
| `monthly_report` | Job diario a `notify_hour` el día 1 | `report:<YYYY-MM del mes anterior>` | "Tu reporte de octubre está listo" (`url` = `/reportes?tab=mes&mes=YYYY-MM`) |
| `test` | `POST /notifications/test` | `test:<timestamp>` | "Bolsillo: aviso de prueba" |

- Un tipo desactivado en preferencias no crea aviso. Montos con formato es-CO (`$ 1.234.500`, pesos enteros).
- Si el servicio push responde 404/410 la suscripción se elimina. Otros errores se registran en log y no fallan la petición del usuario.
- Configuración del servidor: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (`mailto:...`). Se generan con `python -m app.cli gen-vapid`. Sin claves, la app funciona y solo se usa la bandeja.
