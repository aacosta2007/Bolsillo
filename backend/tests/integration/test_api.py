from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.application.ports import today_in
from tests.integration.conftest import PASSWORD, login, make_user

V1 = "/api/v1"
TODAY = today_in("America/Bogota")
MONTH = TODAY.strftime("%Y-%m")


async def mk_account(api, name="Bancolombia", initial="0", **extra):
    r = await api.post(f"{V1}/accounts", json={"name": name, "type": "bank", "initial_balance": initial, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def mk_tx(api, **body):
    return await api.post(f"{V1}/transactions", json=body)


def tx_body(account, category, amount="1000", type="expense", day=TODAY, **extra):
    return {
        "type": type, "amount": amount, "date": day.isoformat(),
        "account_id": account["id"], "category_id": category["id"], **extra,
    }


# ---------------- salud / docs ----------------
async def test_health_and_docs(client):
    r = await client.get(f"{V1}/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert (await client.get(f"{V1}/docs")).status_code == 200


async def test_requires_auth(client):
    r = await client.get(f"{V1}/accounts")
    assert r.status_code == 401
    assert "detail" in r.json()


# ---------------- auth ----------------
async def test_login_me_and_cookie(client, user):
    r = await client.post(f"{V1}/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    cookie = r.headers["set-cookie"].lower()
    assert "refresh_token=" in cookie and "httponly" in cookie
    assert "samesite=strict" in cookie and "path=/api/v1/auth" in cookie and "secure" not in cookie

    me = await client.get(f"{V1}/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    data = me.json()
    assert data["email"] == user.email and data["currency"] == "COP" and data["timezone"] == "America/Bogota"
    assert set(data) == {"id", "email", "display_name", "currency", "timezone", "created_at"}
    assert data["created_at"].endswith("Z")


async def test_login_wrong_password_and_rate_limit(client, user):
    for _ in range(5):
        r = await client.post(f"{V1}/auth/login", json={"email": user.email, "password": "mala"})
        assert r.status_code == 401
    # incluso con la clave correcta, ya está bloqueado
    r = await client.post(f"{V1}/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 429


async def test_refresh_rotates_and_logout(client, user):
    await client.post(f"{V1}/auth/login", json={"email": user.email, "password": PASSWORD})
    old = client.cookies.get("refresh_token")
    assert old
    r = await client.post(f"{V1}/auth/refresh")
    assert r.status_code == 200 and "access_token" in r.json()
    new = client.cookies.get("refresh_token")
    assert new and new != old
    # el token viejo ya no sirve (rotación)
    client.cookies.clear()
    client.cookies.set("refresh_token", old, path="/api/v1/auth")
    assert (await client.post(f"{V1}/auth/refresh")).status_code == 401
    # logout revoca el nuevo
    client.cookies.clear()
    client.cookies.set("refresh_token", new, path="/api/v1/auth")
    assert (await client.post(f"{V1}/auth/logout")).status_code == 204
    client.cookies.set("refresh_token", new, path="/api/v1/auth")
    assert (await client.post(f"{V1}/auth/refresh")).status_code == 401


async def test_refresh_without_cookie(client):
    assert (await client.post(f"{V1}/auth/refresh")).status_code == 401


async def test_patch_me_and_change_password(api, user, client):
    r = await api.patch(f"{V1}/auth/me", json={"display_name": "Andrés", "currency": "usd", "timezone": "America/Lima"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Andrés" and r.json()["currency"] == "USD"
    assert (await api.patch(f"{V1}/auth/me", json={"timezone": "No/Existe"})).status_code == 422

    bad = await api.post(f"{V1}/auth/change-password", json={"current_password": "x", "new_password": "nueva-clave-123"})
    assert bad.status_code == 400
    ok = await api.post(f"{V1}/auth/change-password", json={"current_password": PASSWORD, "new_password": "nueva-clave-123"})
    assert ok.status_code == 204
    client.headers.pop("Authorization")
    assert (await client.post(f"{V1}/auth/login", json={"email": user.email, "password": PASSWORD})).status_code == 401
    assert (await client.post(f"{V1}/auth/login", json={"email": user.email, "password": "nueva-clave-123"})).status_code == 200


# ---------------- categorías ----------------
async def test_default_categories_seeded(api, cats):
    assert len(cats) == 15
    assert cats["Comida"]["icon"] == "utensils" and cats["Comida"]["kind"] == "expense"
    assert cats["Salario"]["kind"] == "income"
    r = await api.get(f"{V1}/categories", params={"kind": "income"})
    assert len(r.json()) == 5


async def test_category_crud_and_conflicts(api, cats):
    r = await api.post(f"{V1}/categories", json={"name": "Mascotas", "kind": "expense", "icon": "paw-print", "color": "#112233"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert (await api.post(f"{V1}/categories", json={"name": "mascotas", "kind": "expense"})).status_code == 409
    assert (await api.patch(f"{V1}/categories/{cid}", json={"name": "Perros"})).json()["name"] == "Perros"
    assert (await api.delete(f"{V1}/categories/{cid}")).status_code == 204
    # en uso -> 409
    acc = await mk_account(api)
    assert (await mk_tx(api, **tx_body(acc, cats["Comida"]))).status_code == 201
    assert (await api.delete(f"{V1}/categories/{cats['Comida']['id']}")).status_code == 409


# ---------------- cuentas ----------------
async def test_account_crud_and_balance(api, cats):
    a = await mk_account(api, "Efectivo", "100000")
    assert a["balance"] == "100000.00" and a["initial_balance"] == "100000.00"
    assert a["archived"] is False and a["type"] == "bank"
    b = await mk_account(api, "Ahorros", "0")

    await mk_tx(api, **tx_body(a, cats["Salario"], "500000", "income"))
    await mk_tx(api, **tx_body(a, cats["Comida"], "45000.50"))
    t = await mk_tx(api, type="transfer", amount="30000", date=TODAY.isoformat(), account_id=a["id"], transfer_account_id=b["id"])
    assert t.status_code == 201, t.text

    accs = {x["name"]: x for x in (await api.get(f"{V1}/accounts")).json()}
    assert accs["Efectivo"]["balance"] == "524999.50"  # 100000 + 500000 - 45000.50 - 30000
    assert accs["Ahorros"]["balance"] == "30000.00"
    one = await api.get(f"{V1}/accounts/{a['id']}")
    assert one.json()["balance"] == "524999.50"

    # con movimientos: no se puede eliminar, pero sí archivar
    assert (await api.delete(f"{V1}/accounts/{a['id']}")).status_code == 409
    p = await api.patch(f"{V1}/accounts/{a['id']}", json={"archived": True})
    assert p.status_code == 200 and p.json()["archived"] is True
    assert {x["name"] for x in (await api.get(f"{V1}/accounts")).json()} == {"Ahorros"}
    full = await api.get(f"{V1}/accounts", params={"include_archived": "true"})
    assert len(full.json()) == 2
    # sin movimientos sí se elimina
    c = await mk_account(api, "Vacía")
    assert (await api.delete(f"{V1}/accounts/{c['id']}")).status_code == 204
    assert (await api.get(f"{V1}/accounts/{c['id']}")).status_code == 404


async def test_resources_of_other_user_are_404(api, client):
    acc = await mk_account(api, "Mía")
    await make_user("otro@example.com")
    tok = await login(client, "otro@example.com")
    client.headers["Authorization"] = f"Bearer {tok}"
    assert (await client.get(f"{V1}/accounts/{acc['id']}")).status_code == 404
    assert (await client.patch(f"{V1}/accounts/{acc['id']}", json={"name": "x"})).status_code == 404
    assert (await client.get(f"{V1}/accounts")).json() == []


# ---------------- transacciones ----------------
async def test_transaction_validations(api, cats):
    a = await mk_account(api)
    b = await mk_account(api, "Otra")
    food, salary = cats["Comida"], cats["Salario"]

    async def status(**over):
        body = {**tx_body(a, food), **over}
        body = {k: v for k, v in body.items() if v is not ...}
        return (await mk_tx(api, **body)).status_code

    assert await status() == 201
    assert await status(amount="0") == 400
    assert await status(amount="-5") == 400
    assert await status(category_id=salary["id"]) == 400            # tipo de categoría no coincide
    assert await status(category_id=None) == 400                    # categoría obligatoria
    assert await status(transfer_account_id=b["id"]) == 400         # gasto con destino
    assert await status(type="income") == 400                       # categoría de gasto en ingreso
    assert await status(type="transfer", category_id=None) == 400   # falta destino
    assert await status(type="transfer", transfer_account_id=a["id"], category_id=None) == 400  # mismo destino
    assert await status(type="transfer", transfer_account_id=b["id"]) == 400  # transferencia con categoría
    assert await status(type="transfer", transfer_account_id=b["id"], category_id=None) == 201
    assert await status(amount="10.123") == 422                     # más de 2 decimales
    assert await status(type="otro") == 422
    # cuenta archivada
    await api.patch(f"{V1}/accounts/{b['id']}", json={"archived": True})
    assert await status(account_id=b["id"]) == 400
    assert await status(type="transfer", transfer_account_id=b["id"], category_id=None) == 400
    # recursos inexistentes
    assert await status(account_id="00000000-0000-4000-8000-000000000000") == 404


async def test_transaction_list_filters_update_delete(api, cats):
    a = await mk_account(api)
    d1, d2 = TODAY - timedelta(days=40), TODAY
    await mk_tx(api, **tx_body(a, cats["Comida"], "10000", day=d1, note="Almuerzo con Juan"))
    await mk_tx(api, **tx_body(a, cats["Transporte"], "5000", day=d2, note="Bus"))
    t3 = (await mk_tx(api, **tx_body(a, cats["Salario"], "900000", "income", day=d2))).json()

    r = await api.get(f"{V1}/transactions")
    body = r.json()
    assert body["total"] == 3 and body["page"] == 1 and body["page_size"] == 50 and len(body["items"]) == 3
    assert body["items"][-1]["date"] == d1.isoformat()  # orden desc por fecha
    assert body["items"][0]["amount"] in ("5000.00", "900000.00")

    assert (await api.get(f"{V1}/transactions", params={"q": "almuerzo"})).json()["total"] == 1
    assert (await api.get(f"{V1}/transactions", params={"type": "income"})).json()["total"] == 1
    assert (await api.get(f"{V1}/transactions", params={"from": d2.isoformat()})).json()["total"] == 2
    assert (await api.get(f"{V1}/transactions", params={"to": (d1).isoformat()})).json()["total"] == 1
    assert (await api.get(f"{V1}/transactions", params={"category_id": cats["Bus"]["id"] if "Bus" in cats else cats["Transporte"]["id"]})).json()["total"] == 1
    p = (await api.get(f"{V1}/transactions", params={"page_size": 2, "page": 2})).json()
    assert p["total"] == 3 and len(p["items"]) == 1

    # patch
    u = await api.patch(f"{V1}/transactions/{t3['id']}", json={"amount": 1000000, "note": "Quincena"})
    assert u.status_code == 200 and u.json()["amount"] == "1000000.00" and u.json()["note"] == "Quincena"
    bad = await api.patch(f"{V1}/transactions/{t3['id']}", json={"category_id": cats["Comida"]["id"]})
    assert bad.status_code == 400
    assert (await api.delete(f"{V1}/transactions/{t3['id']}")).status_code == 204
    assert (await api.get(f"{V1}/transactions/{t3['id']}")).status_code == 404


# ---------------- presupuestos ----------------
async def test_budgets_status_copy_and_rules(api, cats):
    a = await mk_account(api)
    food = cats["Comida"]
    r = await api.post(f"{V1}/budgets", json={"category_id": food["id"], "month": MONTH, "amount_limit": "600000"})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["alert_threshold"] == "0.80" and b["spent"] == "0.00" and b["status"] == "ok" and b["month"] == MONTH
    assert (await api.post(f"{V1}/budgets", json={"category_id": food["id"], "month": MONTH, "amount_limit": "1"})).status_code == 409
    assert (await api.post(f"{V1}/budgets", json={"category_id": cats["Salario"]["id"], "month": MONTH, "amount_limit": "1"})).status_code == 400
    assert (await api.post(f"{V1}/budgets", json={"category_id": food["id"], "month": "2026-13", "amount_limit": "1"})).status_code == 422

    await mk_tx(api, **tx_body(a, food, "450000"))
    s = (await api.get(f"{V1}/budgets", params={"month": MONTH})).json()[0]
    assert s["spent"] == "450000.00" and s["remaining"] == "150000.00" and s["percent"] == 75.0 and s["status"] == "ok"

    await mk_tx(api, **tx_body(a, food, "60000"))
    s = (await api.get(f"{V1}/budgets", params={"month": MONTH})).json()[0]
    assert s["percent"] == 85.0 and s["status"] == "warning"

    await mk_tx(api, **tx_body(a, food, "100000"))
    s = (await api.get(f"{V1}/budgets", params={"month": MONTH})).json()[0]
    assert s["status"] == "exceeded" and s["remaining"] == "-10000.00"

    # umbral personalizado
    up = await api.patch(f"{V1}/budgets/{b['id']}", json={"amount_limit": 2000000, "alert_threshold": 0.9})
    assert up.status_code == 200 and up.json()["alert_threshold"] == "0.90" and up.json()["status"] == "ok"

    # copiar
    nxt = (TODAY.replace(day=1) + timedelta(days=32)).strftime("%Y-%m")
    c = await api.post(f"{V1}/budgets/copy", json={"from_month": MONTH, "to_month": nxt})
    assert c.status_code == 200 and len(c.json()) == 1 and c.json()[0]["month"] == nxt and c.json()[0]["spent"] == "0.00"
    again = await api.post(f"{V1}/budgets/copy", json={"from_month": MONTH, "to_month": nxt})
    assert again.json() == []
    assert len((await api.get(f"{V1}/budgets", params={"month": nxt})).json()) == 1

    # categoría con presupuesto no se puede borrar
    assert (await api.delete(f"{V1}/categories/{food['id']}")).status_code == 409
    assert (await api.delete(f"{V1}/budgets/{b['id']}")).status_code == 204


# ---------------- recurrentes ----------------
async def test_recurring_run_is_idempotent(api, cats):
    a = await mk_account(api)
    start = TODAY - timedelta(days=65)
    r = await api.post(f"{V1}/recurring", json={
        "type": "expense", "amount": "39900", "account_id": a["id"], "category_id": cats["Suscripciones"]["id"],
        "note": "Netflix", "frequency": "monthly", "interval": 1, "start_date": start.isoformat(),
    })
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["next_run_date"] == start.isoformat() and rule["active"] is True and rule["end_date"] is None

    first = await api.post(f"{V1}/recurring/run")
    assert first.status_code == 200
    created = first.json()["created"]
    assert created in (2, 3)  # 65 días atrás: 2 o 3 ocurrencias mensuales según el día
    again = await api.post(f"{V1}/recurring/run")
    assert again.json() == {"created": 0}

    txs = (await api.get(f"{V1}/transactions")).json()
    assert txs["total"] == created and all(t["recurring_id"] == rule["id"] for t in txs["items"])
    rules = (await api.get(f"{V1}/recurring")).json()
    assert date.fromisoformat(rules[0]["next_run_date"]) > TODAY

    up = (await api.get(f"{V1}/recurring/upcoming", params={"days": 60})).json()
    assert len(up) >= 1 and up[0]["rule_id"] == rule["id"] and up[0]["amount"] == "39900.00"
    assert [i["date"] for i in up] == sorted(i["date"] for i in up)

    assert (await api.patch(f"{V1}/recurring/{rule['id']}", json={"active": False})).json()["active"] is False
    assert (await api.get(f"{V1}/recurring/upcoming")).json() == []
    assert (await api.delete(f"{V1}/recurring/{rule['id']}")).status_code == 204
    # los movimientos generados se conservan
    assert (await api.get(f"{V1}/transactions")).json()["total"] == created


async def test_recurring_validation(api, cats):
    a = await mk_account(api)
    base = {"type": "expense", "amount": "10", "account_id": a["id"], "category_id": cats["Salario"]["id"],
            "frequency": "weekly", "start_date": TODAY.isoformat()}
    assert (await api.post(f"{V1}/recurring", json=base)).status_code == 400  # categoría de otro tipo
    assert (await api.post(f"{V1}/recurring", json={**base, "category_id": cats["Comida"]["id"], "type": "transfer"})).status_code == 400
    assert (await api.post(f"{V1}/recurring", json={**base, "category_id": cats["Comida"]["id"], "end_date": (TODAY - timedelta(days=1)).isoformat()})).status_code == 400


# ---------------- metas ----------------
async def test_goals_and_contributions(api):
    target = date(TODAY.year + 1, TODAY.month, 1)
    r = await api.post(f"{V1}/goals", json={"name": "Viaje", "target_amount": "3000000", "target_date": target.isoformat(), "icon": "plane"})
    assert r.status_code == 201, r.text
    g = r.json()
    assert g["saved"] == "0.00" and g["percent"] == 0.0 and g["completed"] is False
    assert g["monthly_needed"] == "250000.00"  # 3.000.000 / 12 meses

    c1 = await api.post(f"{V1}/goals/{g['id']}/contributions", json={"amount": "750000", "date": TODAY.isoformat()})
    assert c1.status_code == 201 and c1.json()["amount"] == "750000.00" and c1.json()["goal_id"] == g["id"]
    goal = (await api.get(f"{V1}/goals")).json()[0]
    assert goal["saved"] == "750000.00" and goal["percent"] == 25.0
    assert goal["monthly_needed"] == "187500.00"

    # retiro válido y retiro excesivo
    assert (await api.post(f"{V1}/goals/{g['id']}/contributions", json={"amount": "-250000"})).status_code == 201
    over = await api.post(f"{V1}/goals/{g['id']}/contributions", json={"amount": "-600000"})
    assert over.status_code == 400
    assert (await api.post(f"{V1}/goals/{g['id']}/contributions", json={"amount": "0"})).status_code == 400

    lst = (await api.get(f"{V1}/goals/{g['id']}/contributions")).json()
    assert len(lst) == 2 and set(lst[0]) == {"id", "goal_id", "amount", "date", "note"}
    # no se puede borrar el aporte que deja el saldo negativo
    pos = next(c for c in lst if c["amount"] == "750000.00")
    assert (await api.delete(f"{V1}/goals/{g['id']}/contributions/{pos['id']}")).status_code == 400

    # completar
    await api.post(f"{V1}/goals/{g['id']}/contributions", json={"amount": "2500000"})
    done = (await api.get(f"{V1}/goals")).json()[0]
    assert done["completed"] is True and done["monthly_needed"] is None and done["percent"] == 100.0

    assert (await api.patch(f"{V1}/goals/{g['id']}", json={"name": "Cartagena"})).json()["name"] == "Cartagena"
    assert (await api.delete(f"{V1}/goals/{g['id']}")).status_code == 204
    assert (await api.get(f"{V1}/goals")).json() == []


async def test_goal_without_date(api):
    g = (await api.post(f"{V1}/goals", json={"name": "Fondo", "target_amount": 1000})).json()
    assert g["monthly_needed"] is None and g["target_date"] is None and g["target_amount"] == "1000.00"


# ---------------- dashboard / reportes / export ----------------
async def seed_month(api, cats):
    a = await mk_account(api, "Principal", "1000000")
    b = await mk_account(api, "Ahorros", "0")
    await mk_tx(api, **tx_body(a, cats["Salario"], "3500000", "income"))
    await mk_tx(api, **tx_body(a, cats["Comida"], "600000"))
    await mk_tx(api, **tx_body(a, cats["Transporte"], "200000"))
    await mk_tx(api, type="transfer", amount="500000", date=TODAY.isoformat(), account_id=a["id"], transfer_account_id=b["id"])
    await api.post(f"{V1}/budgets", json={"category_id": cats["Comida"]["id"], "month": MONTH, "amount_limit": "650000"})
    await api.post(f"{V1}/budgets", json={"category_id": cats["Transporte"]["id"], "month": MONTH, "amount_limit": "1000000"})
    return a, b


async def test_dashboard_summary(api, cats):
    await seed_month(api, cats)
    r = await api.get(f"{V1}/dashboard/summary")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["period"]["from"] == TODAY.replace(day=1).isoformat()
    assert d["total_balance"] == "3700000.00"  # 1.000.000 + 3.500.000 - 800.000 (la transferencia no cambia el total)
    assert d["income"] == "3500000.00" and d["expense"] == "800000.00" and d["net"] == "2700000.00"
    assert d["savings_rate"] == 77.1
    assert [c["name"] for c in d["by_category"]] == ["Comida", "Transporte"]
    assert d["by_category"][0]["total"] == "600000.00" and d["by_category"][0]["percent"] == 75.0
    assert len(d["monthly_trend"]) == 6 and d["monthly_trend"][-1]["month"] == MONTH
    assert d["monthly_trend"][-1]["expense"] == "800000.00" and d["monthly_trend"][0]["income"] == "0.00"
    assert {a["name"] for a in d["accounts"]} == {"Principal", "Ahorros"}
    assert len(d["budgets_at_risk"]) == 1 and d["budgets_at_risk"][0]["status"] == "warning"
    assert d["upcoming_recurring"] == []
    assert len(d["recent_transactions"]) == 4

    inv = await api.get(f"{V1}/dashboard/summary", params={"from": "2026-12-31", "to": "2026-01-01"})
    assert inv.status_code == 400
    empty = await api.get(f"{V1}/dashboard/summary", params={"from": "2020-01-01", "to": "2020-01-31"})
    assert empty.json()["income"] == "0.00" and empty.json()["savings_rate"] == 0.0


async def test_reports(api, cats):
    await seed_month(api, cats)
    r = await api.get(f"{V1}/reports/by-category", params={"from": TODAY.replace(day=1).isoformat(), "to": TODAY.isoformat(), "type": "expense"})
    rows = r.json()
    assert [x["name"] for x in rows] == ["Comida", "Transporte"] and rows[0]["count"] == 1
    inc = (await api.get(f"{V1}/reports/by-category", params={"from": TODAY.replace(day=1).isoformat(), "to": TODAY.isoformat(), "type": "income"})).json()
    assert inc[0]["name"] == "Salario" and inc[0]["percent"] == 100.0
    t = (await api.get(f"{V1}/reports/monthly-trend", params={"months": 3})).json()
    assert len(t) == 3 and t[-1]["month"] == MONTH and t[-1]["net"] == "2700000.00"
    assert len((await api.get(f"{V1}/reports/monthly-trend")).json()) == 12


async def test_export_csv(api, cats):
    a, b = await seed_month(api, cats)
    await mk_tx(api, **tx_body(a, cats["Comida"], "1500.5", note="Café, con \"leche\""))
    r = await api.get(f"{V1}/export/csv", params={"from": TODAY.replace(day=1).isoformat(), "to": TODAY.isoformat()})
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    assert r.headers["content-disposition"] == f'attachment; filename="bolsillo_{TODAY.replace(day=1)}_{TODAY}.csv"'
    assert r.content.startswith(b"\xef\xbb\xbf")
    text = r.content.decode("utf-8-sig")
    lines = text.strip().split("\r\n")
    assert lines[0] == "fecha,tipo,monto,cuenta,categoria,cuenta_destino,nota"
    assert len(lines) == 6
    assert any("transferencia,500000.00,Principal,,Ahorros," in ln for ln in lines)
    assert any('1500.50,Principal,Comida,,"Café, con ""leche"""' in ln for ln in lines)


# ---------------- recurrentes por días del mes ----------------
async def test_quincenal_paycheck_run_and_idempotency(api, cats, monkeypatch):
    import app.api.v1.recurring as recurring_api

    a = await mk_account(api)
    fake_today = date(2026, 10, 15)
    monkeypatch.setattr(recurring_api, "today_in", lambda tz: fake_today)
    r = await api.post(f"{V1}/recurring", json={
        "type": "income", "amount": "1000000", "account_id": a["id"], "category_id": cats["Salario"]["id"],
        "note": "Sueldo", "frequency": "monthly_days", "days_of_month": "L,15", "interval": 7,
        "start_date": "2026-09-01", "is_paycheck": True,
    })
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["days_of_month"] == "15,L" and rule["interval"] == 1 and rule["is_paycheck"] is True
    assert rule["weekend_adjust"] == "none" and rule["next_run_date"] == "2026-09-15"
    assert rule["monthly_equivalent"] == "2000000.00"

    assert (await api.post(f"{V1}/recurring/run")).json() == {"created": 3}
    assert (await api.post(f"{V1}/recurring/run")).json() == {"created": 0}  # idempotente
    txs = (await api.get(f"{V1}/transactions")).json()["items"]
    assert sorted(t["date"] for t in txs) == ["2026-09-15", "2026-09-30", "2026-10-15"]
    assert all(t["recurring_id"] == rule["id"] for t in txs)
    assert (await api.get(f"{V1}/recurring")).json()[0]["next_run_date"] == "2026-10-31"


async def test_quincenal_weekend_adjust_and_upcoming_effective_dates(api, cats, monkeypatch):
    import app.api.v1.recurring as recurring_api

    a = await mk_account(api)
    monkeypatch.setattr(recurring_api, "today_in", lambda tz: date(2026, 10, 20))
    r = await api.post(f"{V1}/recurring", json={
        "type": "income", "amount": "1000000", "account_id": a["id"], "category_id": cats["Salario"]["id"],
        "frequency": "monthly_days", "days_of_month": "15,L", "weekend_adjust": "previous_business_day",
        "start_date": "2026-10-16", "is_paycheck": True,
    })
    assert r.status_code == 201, r.text
    assert r.json()["next_run_date"] == "2026-10-31"  # nominal: sábado
    up = (await api.get(f"{V1}/recurring/upcoming", params={"days": 60})).json()
    assert [(i["date"], i["is_paycheck"]) for i in up] == [
        ("2026-10-30", True), ("2026-11-13", True), ("2026-11-30", True), ("2026-12-15", True)]
    # el job genera con la fecha efectiva: el viernes 30 ya vence aunque el nominal sea el sábado 31
    monkeypatch.setattr(recurring_api, "today_in", lambda tz: date(2026, 10, 30))
    assert (await api.post(f"{V1}/recurring/run")).json() == {"created": 1}
    txs = (await api.get(f"{V1}/transactions")).json()["items"]
    assert [t["date"] for t in txs] == ["2026-10-30"]
    assert (await api.post(f"{V1}/recurring/run")).json() == {"created": 0}


async def test_recurring_days_validation(api, cats):
    a = await mk_account(api)
    base = {"type": "income", "amount": "10", "account_id": a["id"], "category_id": cats["Salario"]["id"],
            "start_date": TODAY.isoformat()}
    md = {**base, "frequency": "monthly_days"}
    # is_paycheck solo en ingresos
    assert (await api.post(f"{V1}/recurring", json={
        **md, "days_of_month": "15", "type": "expense", "category_id": cats["Comida"]["id"], "is_paycheck": True,
    })).status_code == 400
    # days_of_month con otra frecuencia / ausente con monthly_days
    assert (await api.post(f"{V1}/recurring", json={**base, "frequency": "monthly", "days_of_month": "15"})).status_code == 400
    assert (await api.post(f"{V1}/recurring", json=md)).status_code == 400
    # formato inválido -> 422
    for bad in ("0", "32", "15,15", "1,2,3,4", "x"):
        assert (await api.post(f"{V1}/recurring", json={**md, "days_of_month": bad})).status_code == 422, bad
    assert (await api.post(f"{V1}/recurring", json={**md, "days_of_month": "15", "weekend_adjust": "x"})).status_code == 422
    # PATCH: formato inválido 422; is_paycheck en gasto 400; recalcula next_run_date
    ok = (await api.post(f"{V1}/recurring", json={**md, "days_of_month": "15,L"})).json()
    assert (await api.patch(f"{V1}/recurring/{ok['id']}", json={"days_of_month": "40"})).status_code == 422
    p = await api.patch(f"{V1}/recurring/{ok['id']}", json={"days_of_month": "L"})
    assert p.status_code == 200 and p.json()["days_of_month"] == "L"
    p = await api.patch(f"{V1}/recurring/{ok['id']}", json={"frequency": "weekly"})
    assert p.json()["days_of_month"] is None
    assert (await api.patch(f"{V1}/recurring/{ok['id']}", json={"frequency": "monthly_days"})).status_code == 400


# ---------------- quincenas de pago ----------------
def _fix_today(monkeypatch, d):
    import app.api.v1.recurring as recurring_api
    import app.application.reports as reports

    monkeypatch.setattr(reports, "today_in", lambda tz: d)
    monkeypatch.setattr(recurring_api, "today_in", lambda tz: d)


async def _paycheck_scenario(api, cats):
    a = await mk_account(api)
    b = await mk_account(api, "Ahorros")
    r = await api.post(f"{V1}/recurring", json={
        "type": "income", "amount": "1000000", "account_id": a["id"], "category_id": cats["Salario"]["id"],
        "note": "Sueldo", "frequency": "monthly_days", "days_of_month": "15,L",
        "weekend_adjust": "previous_business_day", "start_date": "2026-10-01", "is_paycheck": True,
    })
    assert r.status_code == 201, r.text
    for day, amount in (("2026-10-15", "1000000"), ("2026-10-30", "1000000"), ("2026-11-13", "1000000")):
        r = await mk_tx(api, **tx_body(a, cats["Salario"], amount, "income", date.fromisoformat(day)))
        assert r.status_code == 201, r.text
    for day, amount in (("2026-10-16", "200000"), ("2026-10-29", "100000"), ("2026-11-12", "50000"),
                        ("2026-11-14", "300000"), ("2026-11-20", "100000")):
        r = await mk_tx(api, **tx_body(a, cats["Comida"], amount, day=date.fromisoformat(day)))
        assert r.status_code == 201, r.text
    r = await mk_tx(api, type="transfer", amount="999999", date="2026-11-15", account_id=a["id"],
                    transfer_account_id=b["id"])
    assert r.status_code == 201, r.text


async def test_pay_periods_with_paycheck_rule(api, cats, monkeypatch):
    _fix_today(monkeypatch, date(2026, 11, 20))
    await _paycheck_scenario(api, cats)
    r = await api.get(f"{V1}/reports/pay-periods", params={"count": 3})
    assert r.status_code == 200, r.text
    cur, prev, old = r.json()
    assert (cur["start"], cur["end"], cur["days"], cur["source"]) == ("2026-11-13", "2026-11-29", 17, "paycheck")
    assert (cur["days_elapsed"], cur["days_remaining"], cur["in_progress"]) == (8, 10, True)
    assert (cur["income"], cur["expense"], cur["net"]) == ("1000000.00", "400000.00", "600000.00")  # sin transferencia
    assert (cur["spent_per_day"], cur["available_per_day"]) == ("50000.00", "60000.00")
    assert (cur["spent_percent"], cur["time_percent"], cur["status"]) == (40.0, 47.1, "en_curso")
    assert [(c["name"], c["total"], c["percent"]) for c in cur["by_category"]] == [("Comida", "400000.00", 100.0)]
    assert (prev["start"], prev["end"], prev["in_progress"], prev["status"]) == (
        "2026-10-30", "2026-11-12", False, "ahorro")
    assert (prev["income"], prev["expense"], prev["available_per_day"], prev["days_remaining"]) == (
        "1000000.00", "50000.00", None, 0)
    assert (old["start"], old["end"], old["expense"], old["source"]) == (
        "2026-10-15", "2026-10-29", "300000.00", "paycheck")
    # defecto = 6 periodos; los más antiguos caen en el respaldo de calendario
    six = (await api.get(f"{V1}/reports/pay-periods")).json()
    assert len(six) == 6 and six[3]["source"] == "calendar" and six[3]["end"] == "2026-10-14"
    for bad in (0, 25):
        assert (await api.get(f"{V1}/reports/pay-periods", params={"count": bad})).status_code == 422


async def test_dashboard_pay_period_fields(api, cats, monkeypatch):
    _fix_today(monkeypatch, date(2026, 11, 20))
    await _paycheck_scenario(api, cats)
    d = (await api.get(f"{V1}/dashboard/summary")).json()
    assert d["current_pay_period"]["start"] == "2026-11-13" and d["current_pay_period"]["net"] == "600000.00"
    assert d["previous_pay_period"]["start"] == "2026-10-30" and d["previous_pay_period"]["status"] == "ahorro"
    assert d["next_payday"] == {"date": "2026-11-30", "amount": "1000000.00", "note": "Sueldo"}
    assert "period" in d and "recent_transactions" in d  # campos existentes intactos


async def test_pay_periods_calendar_fallback_without_paycheck(api, cats, monkeypatch):
    _fix_today(monkeypatch, date(2026, 10, 25))
    a = await mk_account(api)
    await mk_tx(api, **tx_body(a, cats["Comida"], "30000", day=date(2026, 10, 20)))
    await mk_tx(api, **tx_body(a, cats["Salario"], "500000", "income", date(2026, 10, 10)))
    periods = (await api.get(f"{V1}/reports/pay-periods", params={"count": 2})).json()
    assert [(p["start"], p["end"], p["source"]) for p in periods] == [
        ("2026-10-16", "2026-10-31", "calendar"), ("2026-10-01", "2026-10-15", "calendar")]
    assert periods[0]["expense"] == "30000.00" and periods[0]["days_elapsed"] == 10
    assert periods[1]["income"] == "500000.00"
    d = (await api.get(f"{V1}/dashboard/summary")).json()
    assert d["next_payday"] is None and d["current_pay_period"]["source"] == "calendar"
    assert d["previous_pay_period"]["start"] == "2026-10-01"
