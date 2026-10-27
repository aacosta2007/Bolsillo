"""Quincenas desde sueldos reales (registrados) + calendario futuro: caso del usuario y variantes."""
from datetime import date
from decimal import Decimal

import pytest

from app.application.notification_triggers import NotificationTriggers
from app.application.notifications import NotificationService
from app.application.recurring import RecurringService
from app.application.reports import ReportService
from app.domain.entities import Category, Transaction
from app.domain.enums import CategoryKind
from app.domain.insights import generate_insights
from app.domain.pay_periods import PeriodSource, merge_pay_dates
from tests.unit.fakes import FakePushSender, FakeUoW, seed
from tests.unit.report_builders import make_report, period as built_period

D = Decimal
TODAY = date(2026, 10, 26)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("app.application.reports.today_in", lambda tz: TODAY)


@pytest.fixture
async def env():
    uow = FakeUoW()
    user, acc, _, food, salary_cat = await seed(uow)
    other_income = Category(user_id=user.id, name="Otros ingresos", kind=CategoryKind.INCOME)
    await uow.categories.add(other_income)
    return uow, user, acc, food, salary_cat, other_income


async def tx(uow, user, acc, cat, kind, amount, when, **kw):
    await uow.transactions.add(
        Transaction(user_id=user.id, type=kind, amount=D(amount), date=when, account_id=acc.id,
                    category_id=cat.id, **kw)
    )


async def user_case(env, adjust="none"):
    """Datos reales del usuario: regla 'Sueldo' desde el 31 oct, sueldo y extra a mano, gastos 16-26."""
    uow, user, acc, food, salary_cat, other_income = env
    await RecurringService(uow).create(user.id, {
        "type": "income", "amount": D("930000"), "account_id": acc.id, "category_id": salary_cat.id,
        "note": "Sueldo", "frequency": "monthly_days", "days_of_month": "15,L",
        "weekend_adjust": adjust, "is_paycheck": True, "start_date": date(2026, 10, 31),
    })
    await tx(uow, user, acc, salary_cat, "income", "930000", date(2026, 10, 15), note="pago de la quincena")
    await tx(uow, user, acc, other_income, "income", "200000", date(2026, 10, 20), note="Papa")
    await tx(uow, user, acc, food, "expense", "700000", date(2026, 10, 18))
    await tx(uow, user, acc, food, "expense", "305900", date(2026, 10, 26))
    return ReportService(uow), user


@pytest.mark.parametrize(
    "adjust,end", [("none", date(2026, 10, 30)), ("previous_business_day", date(2026, 10, 29))]
)
async def test_user_case_manual_salary_with_future_rule(env, adjust, end):
    svc, user = await user_case(env, adjust)
    cur, prev = await svc.pay_periods(user.id, 2)
    assert (cur.start, cur.end, cur.source.value, cur.in_progress) == (date(2026, 10, 15), end, "paycheck", True)
    assert (cur.income, cur.salary_income, cur.extra_income) == (D("1130000.00"), D("930000.00"), D("200000.00"))
    assert (cur.expense, cur.net, cur.status.value) == (D("1005900.00"), D("124100.00"), "en_curso")
    assert cur.available_per_day == D("124100.00") / cur.days_remaining
    assert (prev.start, prev.end, prev.source.value, prev.status.value) == (
        date(2026, 10, 1), date(2026, 10, 14), "calendar", "calendario")


async def test_user_case_payday_inputs(env):
    svc, user = await user_case(env)
    dates, upcoming = await svc.pay_dates(user.id, TODAY)
    assert dates == [date(2026, 10, 15), date(2026, 10, 31)]
    assert [p.date for p in upcoming] == [date(2026, 10, 31)]  # next_payday sale de las reglas


async def test_rule_generated_salary_defines_periods(env):
    uow, user, acc, _, salary_cat, _ = env
    rules = RecurringService(uow)
    await rules.create(user.id, {
        "type": "income", "amount": D("1000000"), "account_id": acc.id, "category_id": salary_cat.id,
        "frequency": "monthly_days", "days_of_month": "15,L", "is_paycheck": True,
        "start_date": date(2026, 9, 1),
    })
    await rules.run(user.id, TODAY)  # genera 15 sep, 30 sep, 15 oct
    cur, prev = await ReportService(uow).pay_periods(user.id, 2)
    assert (cur.start, cur.end) == (date(2026, 10, 15), date(2026, 10, 30))
    assert (prev.start, prev.end, prev.source.value) == (date(2026, 9, 30), date(2026, 10, 14), "paycheck")
    assert (cur.salary_income, cur.extra_income) == (D("1000000.00"), D("0.00"))


async def test_inactive_rule_category_does_not_mark_manual_salary(env):
    uow, user, acc, _, salary_cat, _ = env
    rule = await RecurringService(uow).create(user.id, {
        "type": "income", "amount": D("1"), "account_id": acc.id, "category_id": salary_cat.id,
        "frequency": "monthly", "is_paycheck": True, "start_date": date(2026, 12, 1),
    })
    rule.active = False
    await uow.recurring.update(rule)
    await tx(uow, user, acc, salary_cat, "income", "500000", date(2026, 10, 20))
    cur = (await ReportService(uow).pay_periods(user.id, 1))[0]
    assert cur.source.value == "calendar" and cur.salary_income == D("0.00")
    assert cur.extra_income == D("500000.00")


async def test_scheduled_payday_that_never_arrived_creates_no_period(env):
    uow, user, acc, _, salary_cat, _ = env
    await RecurringService(uow).create(user.id, {
        "type": "income", "amount": D("1000000"), "account_id": acc.id, "category_id": salary_cat.id,
        "frequency": "monthly_days", "days_of_month": "15,L", "is_paycheck": True,
        "start_date": date(2026, 10, 1),
    })  # el 15 oct tocaba, pero no se registró ni se generó
    svc = ReportService(uow)
    dates, _ = await svc.pay_dates(user.id, TODAY)
    assert dates == [date(2026, 10, 31)]
    cur = (await svc.pay_periods(user.id, 1))[0]
    assert (cur.start, cur.end, cur.source.value) == (date(2026, 10, 16), date(2026, 10, 30), "calendar")


async def test_without_paycheck_rules_calendar_and_closed_status(env):
    uow, user, acc, food, _, other = env
    await tx(uow, user, acc, other, "income", "300000", date(2026, 10, 5))
    await tx(uow, user, acc, food, "expense", "900000", date(2026, 10, 6))  # sería déficit, pero sin juicio
    cur, prev = await ReportService(uow).pay_periods(user.id, 2)
    assert (cur.source.value, cur.status.value, cur.start, cur.end) == (
        "calendar", "en_curso", date(2026, 10, 16), date(2026, 10, 31))
    assert (prev.source.value, prev.status.value, prev.net) == ("calendar", "calendario", D("-600000.00"))
    assert prev.salary_income == D("0.00") and prev.extra_income == D("300000.00")


def test_merge_pay_dates_within_three_days_keeps_first_and_dedupes():
    real = [date(2026, 10, 15), date(2026, 10, 15), date(2026, 10, 17), date(2026, 10, 24)]
    future = [date(2026, 10, 25), date(2026, 10, 27), date(2026, 10, 30), date(2026, 11, 2), date(2026, 11, 15)]
    # 15 y 17 se funden (queda 15); 24 es real; 25 (calendario pasado) no cuenta; 27 se funde con 24;
    # 30 queda a 6 días de 24; 2 nov está a 3 días de 30 -> se funde; 15 nov se conserva
    assert merge_pay_dates(real, future, TODAY) == [
        date(2026, 10, 15), date(2026, 10, 24), date(2026, 10, 30), date(2026, 11, 15)]
    # sueldo adelantado 2 días: el real (28) absorbe al de calendario (30)
    assert merge_pay_dates([date(2026, 10, 28)], [date(2026, 10, 30)], date(2026, 10, 28)) == [date(2026, 10, 28)]
    # a 4 días ya son dos fechas distintas
    assert merge_pay_dates([date(2026, 10, 15)], [date(2026, 10, 19)], TODAY) == [date(2026, 10, 15)]
    assert merge_pay_dates([date(2026, 10, 15)], [date(2026, 10, 19)], date(2026, 10, 15)) == [
        date(2026, 10, 15), date(2026, 10, 19)]


def test_insights_do_not_judge_calendar_periods():
    r = make_report()
    deficit = built_period(date(2026, 10, 1), date(2026, 10, 14), 100, 900)
    deficit.source = PeriodSource.CALENDAR
    r.pay_periods = [deficit, built_period(date(2026, 10, 15), date(2026, 10, 30), 1000, 500)]
    text = " ".join(i.text for i in generate_insights(r))
    assert "déficit" not in text and "cerró" not in text


async def test_payday_notification_still_uses_current_period(env):
    uow, user, acc, _, salary_cat, _ = env
    rules = RecurringService(uow)
    await rules.create(user.id, {
        "type": "income", "amount": D("1000000"), "account_id": acc.id, "category_id": salary_cat.id,
        "note": "Sueldo", "frequency": "monthly_days", "days_of_month": "26,30", "is_paycheck": True,
        "start_date": TODAY,
    })
    assert await rules.run(user.id, TODAY) == 1
    await NotificationTriggers(uow, NotificationService(uow, FakePushSender())).paychecks_generated(
        user, rules.paychecks)
    [n] = uow.notifications.items
    assert n.kind == "payday" and "$ 1.000.000" in n.title
    # el sueldo de hoy abre la quincena 26-29 oct (4 días): 250.000 por día
    assert "$ 250.000" in n.body and "29 oct" in n.body


def test_pdf_period_card_shows_salary_and_extra_only_when_extra():
    from app.domain.pay_periods import PeriodSpan, period_metrics
    from app.infrastructure.reporting.viewmodel import _period_card

    span = PeriodSpan(start=date(2026, 10, 15), end=date(2026, 10, 30), source=PeriodSource.PAYCHECK)
    with_extra = _period_card(period_metrics(span, TODAY, D("1130000"), D("0"), D("930000")))
    nb = lambda t: t.replace(" ", " ")  # noqa: E731  (format_cop usa espacio duro)
    assert with_extra["received"] == [("Sueldo", nb("$ 930.000")), ("Extra", nb("$ 200.000"))]
    assert with_extra["per_day"] == "Sin gastos"
    plain = _period_card(period_metrics(span, TODAY, D("930000"), D("100000"), D("930000")))
    assert plain["received"] == [("Recibido", nb("$ 930.000"))]
    cal = PeriodSpan(start=date(2026, 10, 1), end=date(2026, 10, 14), source=PeriodSource.CALENDAR)
    assert _period_card(period_metrics(cal, TODAY, D("0"), D("0")))["status"] == "calendario"
