from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.notification_triggers import NotificationTriggers, run_daily_notifications
from app.application.notifications import NotificationService
from app.application.ports import NullPushSender, PushResult, PushTarget, today_in
from app.application.recurring import RecurringService
from app.core.config import Settings
from app.domain import notification_texts as texts
from app.domain.entities import Budget, RecurringRule, Transaction, User
from app.domain.enums import NotificationKind, TransactionType
from app.domain.exceptions import BusinessRuleError, NotFoundError
from app.domain.formatting import format_cop, format_percent, short_date
from app.domain.notification_schedule import users_due
from app.domain.rules import first_of_month
from tests.unit.fakes import FakePushSender, FakeUoW, seed

D = Decimal
KIND = NotificationKind


# ---------- formato es-CO ----------
@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "$ 0"),
        (999, "$ 999"),
        (1000, "$ 1.000"),
        (1234500, "$ 1.234.500"),
        (D("1234500.00"), "$ 1.234.500"),
        (D("1999.50"), "$ 2.000"),  # redondea a pesos enteros
        (D("20000.49"), "$ 20.000"),
        (D("1000000"), "$ 1.000.000"),
        (-1500, "-$ 1.500"),
    ],
)
def test_format_cop(value, expected):
    assert format_cop(value) == expected


def test_format_percent_and_short_date():
    assert format_percent(85.0) == "85 %"
    assert format_percent(84.6) == "85 %"
    assert short_date(date(2026, 10, 29)) == "29 oct"


# ---------- textos ----------
def test_budget_warning_text():
    m = texts.budget_warning("Comida", 85.0, D("90000"), 11)
    assert m.title == "Comida llegó al 85 %"
    assert m.body == "Te quedan $ 90.000 de tu presupuesto para 11 días."
    assert m.url == "/presupuestos"
    assert texts.budget_warning("Comida", 85.0, D("90000"), 1).body.endswith("para 1 día.")
    assert texts.budget_warning("Comida", 85.0, D("90000"), None).body == "Te quedan $ 90.000 de tu presupuesto."


def test_budget_exceeded_text():
    m = texts.budget_exceeded("Entretenimiento", D("120000"), D("100000"))
    assert m.title == "Entretenimiento excedido: te pasaste por $ 20.000"
    assert "$ 120.000" in m.body and "$ 100.000" in m.body


def test_upcoming_text():
    m = texts.upcoming_recurring("Arriendo", D("1200000"), "Bancolombia", False, date(2026, 11, 1), 1)
    assert m.title == "Mañana: Arriendo $ 1.200.000 desde Bancolombia"
    assert texts.upcoming_recurring("Freelance", D("500000"), "Nu", True, date(2026, 11, 1), 0).title == (
        "Hoy: Freelance $ 500.000 en Nu"
    )
    assert texts.upcoming_recurring("X", D("1000"), None, False, date(2026, 11, 3), 3).title == "En 3 días: X $ 1.000"


def test_payday_text():
    m = texts.payday(D("1000000"), D("66600.00"), date(2026, 10, 29))
    assert m.title == "Llegó tu quincena: $ 1.000.000"
    assert m.body == "Puedes gastar ≈ $ 66.600 por día hasta el 29 oct."
    assert "≈" not in texts.payday(D("1000000"), None, None).body


def test_monthly_report_text():
    m = texts.monthly_report(date(2026, 10, 1))
    assert m.title == "Tu reporte de octubre está listo"
    assert m.url == "/reportes?tab=mes&mes=2026-10"


# ---------- sender nulo / configuración ----------
async def test_null_sender_does_nothing():
    s = NullPushSender()
    assert s.enabled is False
    assert await s.send(PushTarget("https://x", "k", "a"), {}) == PushResult.FAILED


def test_build_sender_depends_on_keys():
    from app.infrastructure.push import build_push_sender
    from app.infrastructure.push.webpush_sender import WebPushSender

    base = {"jwt_secret": "x" * 32}
    assert isinstance(build_push_sender(Settings(**base)), NullPushSender)
    only_public = Settings(**base, vapid_public_key="pub")
    assert isinstance(build_push_sender(only_public), NullPushSender)
    assert isinstance(
        build_push_sender(Settings(**base, vapid_public_key="pub", vapid_private_key="priv")), WebPushSender
    )


def test_generate_vapid_keys_format():
    import base64

    from app.infrastructure.push.vapid import generate_vapid_keys

    public, private = generate_vapid_keys()
    pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
    assert "=" not in public and "=" not in private and "+" not in public and "/" not in public
    raw = base64.urlsafe_b64decode(pad(public))
    assert len(raw) == 65 and raw[0] == 4  # punto P-256 sin comprimir
    assert len(base64.urlsafe_b64decode(pad(private))) == 32


async def test_webpush_sender_maps_errors(monkeypatch):
    from pywebpush import WebPushException

    from app.infrastructure.push import webpush_sender as mod

    calls = []

    def fake(**kw):
        calls.append(kw)
        endpoint = kw["subscription_info"]["endpoint"]
        if endpoint.endswith("/gone"):
            raise WebPushException("gone", response=SimpleNamespace(status_code=410))
        if endpoint.endswith("/missing"):
            raise WebPushException("nf", response=SimpleNamespace(status_code=404))
        if endpoint.endswith("/boom"):
            raise WebPushException("boom", response=SimpleNamespace(status_code=500))
        if endpoint.endswith("/crash"):
            raise RuntimeError("red caída")

    monkeypatch.setattr(mod, "webpush", fake)
    sender = mod.WebPushSender("priv", "mailto:a@b.co")
    t = lambda name: PushTarget(f"https://push.example/{name}", "p", "a")  # noqa: E731
    assert await sender.send(t("ok"), {"title": "ñ"}) == PushResult.OK
    assert await sender.send(t("gone"), {}) == PushResult.GONE
    assert await sender.send(t("missing"), {}) == PushResult.GONE
    assert await sender.send(t("boom"), {}) == PushResult.FAILED
    assert await sender.send(t("crash"), {}) == PushResult.FAILED
    assert calls[0]["ttl"] > 0 and calls[0]["vapid_claims"]["sub"] == "mailto:a@b.co"
    assert '"title": "ñ"' in calls[0]["data"]


# ---------- servicio ----------
@pytest.fixture
async def env():
    uow = FakeUoW()
    user, acc, acc2, expense, income = await seed(uow)
    sender = FakePushSender()
    svc = NotificationService(uow, sender)
    return uow, user, acc, expense, sender, svc


async def test_notify_dedupes_and_pushes_to_every_subscription(env):
    uow, user, _, _, sender, svc = env
    await svc.subscribe(user.id, "https://push/1", "p1", "a1", "Android")
    await svc.subscribe(user.id, "https://push/2", "p2", "a2", None)
    n = await svc.notify(user.id, KIND.PAYDAY, "payday:r:2026-10-15", "T", "B", "/")
    assert n is not None and len(sender.sent) == 2
    payload = sender.sent[0][1]
    assert payload == {"title": "T", "body": "B", "url": "/", "tag": "payday:payday:r:2026-10-15",
                       "notification_id": str(n.id)}
    # misma dedupe_key: ni bandeja ni envío
    assert await svc.notify(user.id, KIND.PAYDAY, "payday:r:2026-10-15", "T", "B", "/") is None
    assert len(uow.notifications.items) == 1 and len(sender.sent) == 2


async def test_dedupe_is_per_user(env):
    uow, user, *_rest, svc = env
    other = User(email="otro@b.co", password_hash="x")
    await uow.users.add(other)
    assert await svc.notify(user.id, KIND.PAYDAY, "k", "T", "B") is not None
    assert await svc.notify(other.id, KIND.PAYDAY, "k", "T", "B") is not None


@pytest.mark.parametrize(
    "kind,pref",
    [
        (KIND.BUDGET_WARNING, "budget_alerts"),
        (KIND.BUDGET_EXCEEDED, "budget_alerts"),
        (KIND.UPCOMING_RECURRING, "upcoming_alerts"),
        (KIND.PAYDAY, "payday_alerts"),
        (KIND.MONTHLY_REPORT, "monthly_report_alerts"),
    ],
)
async def test_disabled_preference_creates_nothing(env, kind, pref):
    uow, user, _, _, sender, svc = env
    await svc.subscribe(user.id, "https://push/1", "p", "a", None)
    await svc.update_preferences(user.id, {pref: False})
    assert await svc.notify(user.id, kind, "k", "T", "B") is None
    assert uow.notifications.items == [] and sender.sent == []


async def test_test_notification_ignores_preferences_and_counts(env):
    uow, user, _, _, sender, svc = env
    await svc.update_preferences(user.id, {"budget_alerts": False, "payday_alerts": False})
    await svc.subscribe(user.id, "https://push/1", "p", "a", None)
    stats = await svc.send_test(user.id)
    assert (stats.sent, stats.failed) == (1, 0)
    assert uow.notifications.items[0].kind == "test"
    assert uow.notifications.items[0].dedupe_key.startswith("test:")


async def test_gone_subscription_is_deleted_and_failures_counted(env):
    uow, user, *_ = env
    sender = FakePushSender({"https://push/gone": PushResult.GONE, "https://push/err": PushResult.FAILED})
    svc = NotificationService(uow, sender)
    for ep in ("https://push/ok", "https://push/gone", "https://push/err"):
        await svc.subscribe(user.id, ep, "p", "a", None)
    stats = await svc.send_test(user.id)
    assert (stats.sent, stats.failed) == (1, 2)
    left = sorted(s.endpoint for s in await uow.push_subscriptions.list_for_user(user.id))
    assert left == ["https://push/err", "https://push/ok"]  # solo 404/410 borra


async def test_sender_exception_never_breaks_notify(env):
    uow, user, *_ = env

    class Boom(FakePushSender):
        async def send(self, target, payload):
            raise RuntimeError("fallo")

    svc = NotificationService(uow, Boom())
    await svc.subscribe(user.id, "https://push/1", "p", "a", None)
    assert await svc.notify(user.id, KIND.PAYDAY, "k", "T", "B") is not None
    assert len(uow.notifications.items) == 1


async def test_null_sender_keeps_inbox_only(env):
    uow, user, *_ = env
    svc = NotificationService(uow, NullPushSender())
    await svc.subscribe(user.id, "https://push/1", "p", "a", None)
    assert await svc.notify(user.id, KIND.PAYDAY, "k", "T", "B") is not None
    stats = await svc.send_test(user.id)
    assert (stats.sent, stats.failed) == (0, 0) and len(uow.notifications.items) == 2


async def test_preferences_validation_and_inbox(env):
    uow, user, _, _, _, svc = env
    prefs = await svc.update_preferences(user.id, {"notify_hour": 20, "upcoming_days_before": 3})
    assert (prefs.notify_hour, prefs.upcoming_days_before) == (20, 3)
    with pytest.raises(BusinessRuleError):
        await svc.update_preferences(user.id, {"notify_hour": 24})
    with pytest.raises(BusinessRuleError):
        await svc.update_preferences(user.id, {"upcoming_days_before": 8})

    a = await svc.notify(user.id, KIND.PAYDAY, "a", "A", "x")
    await svc.notify(user.id, KIND.PAYDAY, "b", "B", "x")
    items, total, unread = await svc.list(user.id, False, 1, 30)
    assert (total, unread, items[0].title) == (2, 2, "B")  # más recientes primero
    await svc.mark_read(user.id, a.id)
    _, total_unread, unread = await svc.list(user.id, True, 1, 30)
    assert (total_unread, unread) == (1, 1)
    await svc.mark_all_read(user.id)
    assert (await svc.list(user.id, True, 1, 30))[2] == 0
    with pytest.raises(NotFoundError):
        await svc.mark_read(user.id, user.id)


# ---------- selección por hora local ----------
def test_users_due_uses_local_hour():
    bogota = User(email="a@b.co", password_hash="x", timezone="America/Bogota", notify_hour=8)
    madrid = User(email="m@b.co", password_hash="x", timezone="Europe/Madrid", notify_hour=8)
    night = User(email="n@b.co", password_hash="x", timezone="America/Bogota", notify_hour=23)
    bad_tz = User(email="z@b.co", password_hash="x", timezone="No/Existe", notify_hour=13)
    users = [bogota, madrid, night, bad_tz]
    # 13:00 UTC = 08:00 Bogotá (UTC-5), 14:00 Madrid (CEST, UTC+2) y 13:00 en UTC (zona inválida -> UTC)
    due = users_due(users, datetime(2026, 10, 20, 13, 0, tzinfo=timezone.utc))
    assert [u.email for u, _ in due] == ["a@b.co", "z@b.co"]
    assert due[0][1].hour == 8 and due[0][1].date() == date(2026, 10, 20)
    # 06:00 UTC = 08:00 Madrid (CEST)
    assert [u.email for u, _ in users_due(users, datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc))] == ["m@b.co"]
    # 04:00 UTC = 23:00 del día anterior en Bogotá
    due = users_due(users, datetime(2026, 10, 20, 4, 0, tzinfo=timezone.utc))
    assert [u.email for u, _ in due] == ["n@b.co"] and due[0][1].date() == date(2026, 10, 19)


# ---------- disparadores ----------
TODAY = today_in("America/Bogota")


async def add_expense(uow, user, acc, cat, amount):
    return await uow.transactions.add(Transaction(
        user_id=user.id, type=TransactionType.EXPENSE, amount=D(amount), date=TODAY,
        account_id=acc.id, category_id=cat.id,
    ))


async def test_budget_triggers_warning_then_exceeded_without_repeats(env):
    uow, user, acc, expense, sender, svc = env
    triggers = NotificationTriggers(uow, svc)
    await uow.budgets.add(Budget(user_id=user.id, category_id=expense.id, month=first_of_month(TODAY),
                                 amount_limit=D("100000")))
    tx = await add_expense(uow, user, acc, expense, "50000")
    await triggers.after_transaction(user, tx)
    assert uow.notifications.items == []  # 50 %: nada
    tx = await add_expense(uow, user, acc, expense, "35000")  # 85 %
    await triggers.after_transaction(user, tx)
    kinds = [n.kind for n in uow.notifications.items]
    assert kinds == ["budget_warning"]
    assert uow.notifications.items[0].title == "Comida llegó al 85 %"
    tx = await add_expense(uow, user, acc, expense, "1000")  # sigue en warning: no se repite
    await triggers.after_transaction(user, tx)
    assert len(uow.notifications.items) == 1
    tx = await add_expense(uow, user, acc, expense, "20000")  # 106 %
    await triggers.after_transaction(user, tx)
    await triggers.after_transaction(user, tx)
    assert [n.kind for n in uow.notifications.items] == ["budget_warning", "budget_exceeded"]
    assert uow.notifications.items[1].title == "Comida excedido: te pasaste por $ 6.000"


async def test_budget_trigger_ignores_income_transfer_and_disabled(env):
    uow, user, acc, expense, sender, svc = env
    triggers = NotificationTriggers(uow, svc)
    await uow.budgets.add(Budget(user_id=user.id, category_id=expense.id, month=first_of_month(TODAY),
                                 amount_limit=D("100")))
    income_tx = Transaction(user_id=user.id, type=TransactionType.INCOME, amount=D("500"), date=TODAY,
                            account_id=acc.id, category_id=expense.id)
    await triggers.after_transaction(user, income_tx)
    assert uow.notifications.items == []
    await svc.update_preferences(user.id, {"budget_alerts": False})
    tx = await add_expense(uow, user, acc, expense, "500")
    await triggers.after_transaction(user, tx)
    assert uow.notifications.items == []


async def test_daily_job_budget_backup(env):
    uow, user, acc, expense, sender, svc = env
    await uow.budgets.add(Budget(user_id=user.id, category_id=expense.id, month=first_of_month(TODAY),
                                 amount_limit=D("100000")))
    await add_expense(uow, user, acc, expense, "90000")
    triggers = NotificationTriggers(uow, svc)
    local = datetime.combine(TODAY, datetime.min.time()).replace(hour=8)
    await triggers.daily(user, local)
    await triggers.daily(user, local)
    assert [n.kind for n in uow.notifications.items] == ["budget_warning"]


async def make_rule(uow, user, acc, cat, **over):
    base = {"type": "expense", "amount": D("1200000"), "account_id": acc.id, "category_id": cat.id,
            "note": "Arriendo", "frequency": "monthly", "interval": 1, "start_date": TODAY + timedelta(days=1)}
    base.update(over)
    return await RecurringService(uow).create(user.id, base)


async def test_upcoming_notifies_and_excludes_paycheck(env):
    uow, user, acc, expense, sender, svc = env
    income_cat = (await uow.categories.list(user.id, None))[1]
    await make_rule(uow, user, acc, expense)  # mañana
    await make_rule(uow, user, acc, income_cat, type="income", is_paycheck=True, note="Sueldo")
    await make_rule(uow, user, acc, income_cat, type="income", note="Freelance", amount=D("300000"))
    await make_rule(uow, user, acc, expense, note="Lejano", start_date=TODAY + timedelta(days=5))
    triggers = NotificationTriggers(uow, svc)
    local = datetime.combine(TODAY, datetime.min.time()).replace(hour=8)
    await triggers.daily(user, local)
    titles = sorted(n.title for n in uow.notifications.items)
    assert titles == [
        "Mañana: Arriendo $ 1.200.000 desde Banco",
        "Mañana: Freelance $ 300.000 en Banco",
    ]
    assert all(n.kind == "upcoming_recurring" and n.dedupe_key.startswith("upcoming:") for n in uow.notifications.items)
    await triggers.daily(user, local)  # repetir el job no duplica
    assert len(uow.notifications.items) == 2


async def test_upcoming_respects_preference_and_zero_days(env):
    uow, user, acc, expense, sender, svc = env
    rule = await make_rule(uow, user, acc, expense, start_date=TODAY)
    # el job de las 00:05 ya generó el movimiento de hoy
    await RecurringService(uow).run(user.id, TODAY)
    triggers = NotificationTriggers(uow, svc)
    local = datetime.combine(TODAY, datetime.min.time()).replace(hour=8)

    await svc.update_preferences(user.id, {"upcoming_days_before": 0})
    user = await uow.users.get(user.id)
    await triggers.daily(user, local)
    assert [n.title for n in uow.notifications.items] == ["Hoy: Arriendo $ 1.200.000 desde Banco"]
    assert uow.notifications.items[0].dedupe_key == f"upcoming:{rule.id}:{TODAY.isoformat()}"

    uow.notifications.items.clear()
    await svc.update_preferences(user.id, {"upcoming_alerts": False})
    await triggers.daily(await uow.users.get(user.id), local)
    assert uow.notifications.items == []


async def test_monthly_report_only_on_day_one(env):
    uow, user, _, _, _, svc = env
    triggers = NotificationTriggers(uow, svc)
    await triggers.daily(user, datetime(2026, 10, 15, 8, 0))
    assert uow.notifications.items == []
    await triggers.daily(user, datetime(2026, 11, 1, 8, 0))
    await triggers.daily(user, datetime(2026, 11, 1, 8, 30))
    [n] = uow.notifications.items
    assert (n.kind, n.dedupe_key, n.title) == ("monthly_report", "report:2026-10", "Tu reporte de octubre está listo")
    assert n.url == "/reportes?tab=mes&mes=2026-10"
    # enero -> reporte de diciembre del año anterior
    await triggers.daily(user, datetime(2027, 1, 1, 8, 0))
    assert uow.notifications.items[-1].dedupe_key == "report:2026-12"
    # desactivado
    uow.notifications.items.clear()
    await svc.update_preferences(user.id, {"monthly_report_alerts": False})
    await triggers.daily(await uow.users.get(user.id), datetime(2026, 11, 1, 8, 0))
    assert uow.notifications.items == []


async def test_run_daily_notifications_selects_users_by_local_hour(env):
    uow, user, _, _, sender, _ = env
    user.notify_hour = 8
    other = User(email="m@b.co", password_hash="x", timezone="Europe/Madrid", notify_hour=8)
    await uow.users.add(other)
    now = datetime(2026, 11, 1, 13, 0, tzinfo=timezone.utc)  # 08:00 en Bogotá, 14:00 en Madrid
    processed = await run_daily_notifications(lambda: uow, sender, now)
    assert processed == 1
    assert [n.user_id for n in uow.notifications.items] == [user.id]  # reporte mensual (día 1)


async def test_recurring_run_reports_generated_paychecks(env):
    uow, user, acc, _, _, _ = env
    income_cat = (await uow.categories.list(user.id, None))[1]
    paid = await make_rule(uow, user, acc, income_cat, type="income", is_paycheck=True, note="Sueldo",
                           start_date=TODAY)
    other = await make_rule(uow, user, acc, income_cat, type="income", note="Otro", start_date=TODAY)
    svc = RecurringService(uow)
    assert await svc.run(user.id, TODAY) == 2
    assert [(p.rule_id, p.date, p.amount) for p in svc.paychecks] == [(paid.id, TODAY, D("1200000"))]
    assert other.id not in [p.rule_id for p in svc.paychecks]
    assert await svc.run(user.id, TODAY) == 0 and svc.paychecks == []


async def test_stale_paychecks_are_not_announced(env):
    uow, user, _, _, sender, svc = env
    from app.application.recurring import GeneratedPaycheck

    triggers = NotificationTriggers(uow, svc)
    await triggers.paychecks_generated(
        user, [GeneratedPaycheck(user.id, TODAY - timedelta(days=30), D("1000000"))]
    )
    assert uow.notifications.items == []
