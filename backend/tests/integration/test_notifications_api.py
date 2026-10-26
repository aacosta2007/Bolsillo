import subprocess
import sys
from datetime import datetime, time, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.application.notification_triggers import run_daily_notifications
from app.application.ports import PushResult, today_in
from tests.conftest import ROOT
from tests.integration.conftest import login, make_user
from tests.integration.test_api import MONTH, TODAY, V1, mk_account, tx_body
from tests.unit.fakes import FakePushSender

N = f"{V1}/notifications"
EP = "https://push.example.com/send/abc123"
SUB = {"endpoint": EP, "keys": {"p256dh": "BPubKey", "auth": "authSecret"}, "device": "Android Chrome"}


@pytest_asyncio.fixture
async def sender():
    from app.api.deps import get_push_sender
    from app.main import app

    fake = FakePushSender()
    app.dependency_overrides[get_push_sender] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_push_sender, None)


async def inbox(api, **params):
    r = await api.get(N, params=params)
    assert r.status_code == 200, r.text
    return r.json()


async def kinds(api):
    return [n["kind"] for n in reversed((await inbox(api))["items"])]


async def budget(api, cats, limit="100000", name="Comida"):
    r = await api.post(f"{V1}/budgets", json={"category_id": cats[name]["id"], "month": MONTH, "amount_limit": limit})
    assert r.status_code == 201, r.text
    return r.json()


# ---------- VAPID / suscripciones ----------
async def test_vapid_key_503_without_keys_and_200_with_keys(api, sender):
    from app.core.config import get_settings
    from app.main import app

    r = await api.get(f"{N}/vapid-public-key")
    assert r.status_code == 503 and "detail" in r.json()

    base = get_settings()
    configured = base.model_copy(update={"vapid_public_key": "BLpublic", "vapid_private_key": "priv"})
    app.dependency_overrides[get_settings] = lambda: configured
    try:
        r = await api.get(f"{N}/vapid-public-key")
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert r.status_code == 200 and r.json() == {"public_key": "BLpublic"}


async def test_requires_auth(client):
    assert (await client.get(N)).status_code == 401
    assert (await client.post(f"{N}/test")).status_code == 401


async def test_subscribe_is_upsert_and_unsubscribe(api, sender):
    r = await api.post(f"{N}/subscriptions", json=SUB)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "endpoint", "device", "created_at"} and body["endpoint"] == EP
    r2 = await api.post(f"{N}/subscriptions", json={**SUB, "device": "Pixel"})
    assert r2.status_code == 201 and r2.json()["device"] == "Pixel" and r2.json()["id"] == body["id"]
    assert (await api.post(f"{N}/test")).json() == {"sent": 1, "failed": 0}  # una sola suscripción

    assert (await api.delete(f"{N}/subscriptions", params={"endpoint": EP})).status_code == 204
    assert (await api.post(f"{N}/test")).json() == {"sent": 0, "failed": 0}
    assert (await api.delete(f"{N}/subscriptions", params={"endpoint": EP})).status_code == 204  # idempotente

    bad = await api.post(f"{N}/subscriptions", json={"endpoint": "", "keys": {"p256dh": "a", "auth": "b"}})
    assert bad.status_code == 422
    assert (await api.post(f"{N}/subscriptions", json={"endpoint": EP})).status_code == 422


async def test_subscription_endpoint_moves_between_users(client, api, sender):
    await api.post(f"{N}/subscriptions", json=SUB)
    await make_user("otra@example.com")
    token = await login(client, "otra@example.com")
    r = await client.post(f"{N}/subscriptions", json=SUB, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    assert (await api.post(f"{N}/test")).json() == {"sent": 0, "failed": 0}  # el dispositivo ya es de la otra cuenta
    other = await client.post(f"{N}/test", headers={"Authorization": f"Bearer {token}"})
    assert other.json() == {"sent": 1, "failed": 0}


# ---------- test ----------
async def test_post_test_sends_one_push_and_creates_notification(api, sender):
    await api.post(f"{N}/subscriptions", json=SUB)
    r = await api.post(f"{N}/test")
    assert r.status_code == 200 and r.json() == {"sent": 1, "failed": 0}
    assert len(sender.sent) == 1
    target, payload = sender.sent[0]
    assert target.endpoint == EP and target.p256dh == "BPubKey" and target.auth == "authSecret"
    assert set(payload) == {"title", "body", "url", "tag", "notification_id"}
    assert payload["tag"].startswith("test:test:") and payload["title"] == "Bolsillo: aviso de prueba"
    data = await inbox(api)
    assert data["total"] == 1 and data["unread_count"] == 1
    item = data["items"][0]
    assert item["kind"] == "test" and item["read"] is False and item["id"] == payload["notification_id"]
    assert set(item) == {"id", "kind", "title", "body", "url", "read", "created_at"} and item["created_at"].endswith("Z")
    # dos pruebas seguidas no se deduplican
    await api.post(f"{N}/test")
    assert (await inbox(api))["total"] == 2


async def test_gone_subscription_is_removed_and_inbox_survives(api, sender):
    sender.results[EP] = PushResult.GONE
    await api.post(f"{N}/subscriptions", json=SUB)
    await api.post(f"{N}/subscriptions", json={**SUB, "endpoint": EP + "/ok"})
    assert (await api.post(f"{N}/test")).json() == {"sent": 1, "failed": 1}
    sender.sent.clear()
    assert (await api.post(f"{N}/test")).json() == {"sent": 1, "failed": 0}  # la 410 ya no existe
    assert [t.endpoint for t, _ in sender.sent] == [EP + "/ok"]
    assert (await inbox(api))["total"] == 2


async def test_push_error_does_not_break_request(api, sender):
    sender.results[EP] = PushResult.FAILED
    await api.post(f"{N}/subscriptions", json=SUB)
    assert (await api.post(f"{N}/test")).json() == {"sent": 0, "failed": 1}
    assert len((await api.get(f"{V1}/accounts")).json()) == 0  # la API sigue sana


# ---------- presupuestos ----------
async def test_budget_warning_then_exceeded_via_expenses(api, cats, sender):
    acc = await mk_account(api)
    food = cats["Comida"]
    await api.post(f"{N}/subscriptions", json=SUB)
    b = await budget(api, cats)

    assert (await api.post(f"{V1}/transactions", json=tx_body(acc, food, "50000"))).status_code == 201
    assert await kinds(api) == []
    r = await api.post(f"{V1}/transactions", json=tx_body(acc, food, "35000"))  # 85 %
    assert r.status_code == 201
    assert await kinds(api) == ["budget_warning"]
    assert len(sender.sent) == 1
    note = (await inbox(api))["items"][0]
    assert note["title"] == "Comida llegó al 85 %" and note["url"] == "/presupuestos"
    assert note["body"].startswith("Te quedan $ 15.000 de tu presupuesto")
    payload = sender.sent[0][1]
    assert payload["tag"] == f"budget_warning:budget:{b['id']}:{MONTH}:warning"

    # otro gasto en el mismo estado: no se repite
    await api.post(f"{V1}/transactions", json=tx_body(acc, food, "1000"))
    assert await kinds(api) == ["budget_warning"] and len(sender.sent) == 1

    # excede
    await api.post(f"{V1}/transactions", json=tx_body(acc, food, "20000"))
    assert await kinds(api) == ["budget_warning", "budget_exceeded"]
    exceeded = (await inbox(api))["items"][0]
    assert exceeded["title"] == "Comida excedido: te pasaste por $ 6.000"
    assert len(sender.sent) == 2
    await api.post(f"{V1}/transactions", json=tx_body(acc, food, "500"))
    assert await kinds(api) == ["budget_warning", "budget_exceeded"]


async def test_budget_alert_on_edit_and_disabled_pref(api, cats, sender):
    acc = await mk_account(api)
    food = cats["Comida"]
    await budget(api, cats)
    tx = (await api.post(f"{V1}/transactions", json=tx_body(acc, food, "10000"))).json()
    assert await kinds(api) == []
    r = await api.patch(f"{V1}/transactions/{tx['id']}", json={"amount": "95000"})
    assert r.status_code == 200
    assert await kinds(api) == ["budget_warning"]

    # desactivar presupuestos: ya no se crean avisos
    await api.patch(f"{N}/preferences", json={"budget_alerts": False})
    await api.patch(f"{V1}/transactions/{tx['id']}", json={"amount": "150000"})
    assert await kinds(api) == ["budget_warning"]


async def test_other_categories_and_income_do_not_alert(api, cats, sender):
    acc = await mk_account(api)
    await budget(api, cats, "100")
    other = cats["Transporte"] if "Transporte" in cats else next(c for n, c in cats.items() if c["kind"] == "expense" and n != "Comida")
    await api.post(f"{V1}/transactions", json=tx_body(acc, other, "5000"))
    await api.post(f"{V1}/transactions", json=tx_body(acc, cats["Salario"], "5000", type="income"))
    assert await kinds(api) == []


# ---------- sueldo ----------
async def test_run_with_paycheck_creates_payday_notification(api, cats, sender):
    acc = await mk_account(api)
    await api.post(f"{N}/subscriptions", json=SUB)
    rule = (await api.post(f"{V1}/recurring", json={
        "type": "income", "amount": "1000000", "account_id": acc["id"], "category_id": cats["Salario"]["id"],
        "note": "Sueldo", "frequency": "monthly", "start_date": TODAY.isoformat(), "is_paycheck": True,
    })).json()
    # un recurrente normal no genera aviso de sueldo
    await api.post(f"{V1}/recurring", json={
        "type": "expense", "amount": "5000", "account_id": acc["id"], "category_id": cats["Comida"]["id"],
        "note": "Netflix", "frequency": "monthly", "start_date": TODAY.isoformat(),
    })
    assert (await api.post(f"{V1}/recurring/run")).json() == {"created": 2}
    assert await kinds(api) == ["payday"]
    n = (await inbox(api))["items"][0]
    assert n["title"] == "Llegó tu quincena: $ 1.000.000"
    assert "por día hasta el" in n["body"] and n["body"].startswith("Puedes gastar ≈ $ ")
    assert len(sender.sent) == 1
    assert sender.sent[0][1]["tag"] == f"payday:payday:{rule['id']}:{TODAY.isoformat()}"

    assert (await api.post(f"{V1}/recurring/run")).json() == {"created": 0}  # idempotente
    assert await kinds(api) == ["payday"]


async def test_payday_pref_disabled(api, cats, sender):
    acc = await mk_account(api)
    await api.patch(f"{N}/preferences", json={"payday_alerts": False})
    await api.post(f"{V1}/recurring", json={
        "type": "income", "amount": "1000000", "account_id": acc["id"], "category_id": cats["Salario"]["id"],
        "frequency": "monthly", "start_date": TODAY.isoformat(), "is_paycheck": True,
    })
    await api.post(f"{V1}/recurring/run")
    assert await kinds(api) == []


# ---------- job diario (hora local) ----------
async def test_daily_job_upcoming_and_report_against_db(api, cats, user, sender):
    from app.infrastructure.scheduler import uow_factory

    acc = await mk_account(api, "Bancolombia")
    rent = {"type": "expense", "amount": "1200000", "account_id": acc["id"], "category_id": cats["Comida"]["id"],
            "note": "Arriendo", "frequency": "monthly", "start_date": (TODAY + timedelta(days=1)).isoformat()}
    await api.post(f"{V1}/recurring", json=rent)
    await api.post(f"{V1}/recurring", json={**rent, "type": "income", "category_id": cats["Salario"]["id"],
                                             "note": "Sueldo", "is_paycheck": True})
    await api.post(f"{V1}/recurring", json={**rent, "note": "Lejano", "start_date": (TODAY + timedelta(days=9)).isoformat()})

    at_8_bogota = datetime.combine(TODAY, time(13, 0), tzinfo=timezone.utc)
    at_9_bogota = at_8_bogota + timedelta(hours=1)
    assert await run_daily_notifications(uow_factory, sender, at_9_bogota) == 0  # no es su hora
    assert await kinds(api) == []
    assert await run_daily_notifications(uow_factory, sender, at_8_bogota) == 1
    assert await run_daily_notifications(uow_factory, sender, at_8_bogota) == 1  # repetir no duplica
    items = (await inbox(api))["items"]
    assert [i["title"] for i in items] == ["Mañana: Arriendo $ 1.200.000 desde Bancolombia"]
    assert items[0]["kind"] == "upcoming_recurring"

    # preferencia de hora
    await api.patch(f"{N}/preferences", json={"notify_hour": 9, "upcoming_days_before": 2})
    assert await run_daily_notifications(uow_factory, sender, at_8_bogota) == 0
    assert await run_daily_notifications(uow_factory, sender, at_9_bogota) == 1
    assert await kinds(api) == ["upcoming_recurring"]  # a 2 días no hay nada nuevo


async def test_daily_job_monthly_report_and_budget_backup(api, cats, user, sender):
    from app.infrastructure.scheduler import uow_factory

    # presupuesto ya excedido sin avisos (p. ej. gastos anteriores a la función)
    acc = await mk_account(api)
    await budget(api, cats, "1000")
    await api.patch(f"{N}/preferences", json={"budget_alerts": False})
    await api.post(f"{V1}/transactions", json=tx_body(acc, cats["Comida"], "5000"))
    await api.patch(f"{N}/preferences", json={"budget_alerts": True})
    assert await kinds(api) == []

    now = datetime.combine(TODAY, time(13, 0), tzinfo=timezone.utc)
    await run_daily_notifications(uow_factory, sender, now)
    assert await kinds(api) == ["budget_exceeded"]

    first_next_month = (TODAY.replace(day=1) + timedelta(days=32)).replace(day=1)
    await run_daily_notifications(uow_factory, sender, datetime.combine(first_next_month, time(13, 0), tzinfo=timezone.utc))
    k = await kinds(api)
    assert k.count("monthly_report") == 1
    report = next(i for i in (await inbox(api))["items"] if i["kind"] == "monthly_report")
    assert report["url"] == f"/reportes?tab=mes&mes={MONTH}"


# ---------- preferencias ----------
async def test_preferences_get_patch(api, sender):
    default = {"budget_alerts": True, "upcoming_alerts": True, "upcoming_days_before": 1,
               "payday_alerts": True, "monthly_report_alerts": True, "notify_hour": 8}
    assert (await api.get(f"{N}/preferences")).json() == default
    r = await api.patch(f"{N}/preferences", json={"notify_hour": 20, "upcoming_days_before": 0, "payday_alerts": False})
    assert r.status_code == 200
    expected = {**default, "notify_hour": 20, "upcoming_days_before": 0, "payday_alerts": False}
    assert r.json() == expected and (await api.get(f"{N}/preferences")).json() == expected
    assert (await api.patch(f"{N}/preferences", json={})).json() == expected
    for bad in ({"notify_hour": 24}, {"notify_hour": -1}, {"upcoming_days_before": 8}, {"budget_alerts": "quizá"}):
        assert (await api.patch(f"{N}/preferences", json=bad)).status_code == 422
    # /auth/me no cambia de forma
    me = (await api.get(f"{V1}/auth/me")).json()
    assert set(me) == {"id", "email", "display_name", "currency", "timezone", "created_at"}


# ---------- bandeja ----------
async def test_read_read_all_unread_count_and_pagination(api, sender):
    for _ in range(3):
        await api.post(f"{N}/test")
    data = await inbox(api)
    assert (data["total"], data["unread_count"], data["page"], data["page_size"]) == (3, 3, 1, 30)
    first = data["items"][0]
    assert (await api.post(f"{N}/{first['id']}/read")).status_code == 204
    assert (await api.post(f"{N}/{first['id']}/read")).status_code == 204  # idempotente
    data = await inbox(api)
    assert data["unread_count"] == 2 and next(i for i in data["items"] if i["id"] == first["id"])["read"] is True

    unread = await inbox(api, unread_only="true")
    assert unread["total"] == 2 and all(not i["read"] for i in unread["items"]) and unread["unread_count"] == 2
    page2 = await inbox(api, page=2, page_size=2)
    assert len(page2["items"]) == 1 and page2["total"] == 3 and page2["unread_count"] == 2

    assert (await api.post(f"{N}/read-all")).status_code == 204
    after = await inbox(api)
    assert after["unread_count"] == 0 and after["total"] == 3
    assert (await inbox(api, unread_only="true"))["items"] == []
    assert (await api.get(N, params={"page_size": 101})).status_code == 422


async def test_notifications_are_private_per_user(client, api, sender):
    await api.post(f"{N}/test")
    mine = (await inbox(api))["items"][0]
    await make_user("otra@example.com")
    token = await login(client, "otra@example.com")
    h = {"Authorization": f"Bearer {token}"}
    assert (await client.get(N, headers=h)).json()["total"] == 0
    assert (await client.post(f"{N}/{mine['id']}/read", headers=h)).status_code == 404
    assert (await client.post(f"{N}/{uuid4()}/read", headers=h)).status_code == 404
    assert (await client.post(f"{N}/read-all", headers=h)).status_code == 204
    assert (await inbox(api))["unread_count"] == 1  # la otra cuenta no tocó mis avisos


# ---------- migración ----------
def _alembic(*args):
    res = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    return res


async def test_migration_0003_roundtrip_keeps_existing_users(user):
    from app.infrastructure.db.session import dispose_engine, get_engine

    await dispose_engine()  # sin conexiones abiertas durante el DDL
    _alembic("downgrade", "-1")
    _alembic("upgrade", "head")
    _alembic("check")

    # Usuario creado con el esquema anterior (0002) sobrevive a la migración con valores por defecto
    _alembic("downgrade", "-1")
    async with get_engine().begin() as conn:
        await conn.execute(text(
            "INSERT INTO users (id, email, password_hash, currency, timezone) "
            "VALUES (:id, 'viejo@example.com', 'x', 'COP', 'America/Bogota')"), {"id": uuid4().hex})
    await dispose_engine()
    _alembic("upgrade", "head")
    async with get_engine().connect() as conn:
        row = (await conn.execute(text(
            "SELECT budget_alerts, upcoming_alerts, upcoming_days_before, payday_alerts, "
            "monthly_report_alerts, notify_hour FROM users WHERE email = 'viejo@example.com'"))).one()
    assert tuple(row) == (1, 1, 1, 1, 1, 8)
