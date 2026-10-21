from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.application.budgets import BudgetService
from app.application.goals import GoalService
from app.application.recurring import RecurringService
from app.application.transactions import TransactionService
from app.domain.entities import Category
from app.domain.enums import BudgetState, CategoryKind
from app.domain.exceptions import BusinessRuleError, ConflictError, NotFoundError
from tests.unit.fakes import FakeUoW, seed

D = Decimal
TODAY = date(2026, 10, 18)


@pytest.fixture
async def env():
    uow = FakeUoW()
    user, acc, acc2, expense, income = await seed(uow)
    return uow, user, acc, acc2, expense, income


def data(acc, cat, **over):
    base = {"type": "expense", "amount": D("1000"), "date": TODAY, "account_id": acc.id,
            "category_id": cat.id if cat else None, "transfer_account_id": None, "note": None}
    base.update(over)
    return base


# ---- transacciones ----
async def test_create_valid_expense_income_and_transfer(env):
    uow, user, acc, acc2, expense, income = env
    svc = TransactionService(uow)
    tx = await svc.create(user.id, data(acc, expense))
    assert tx.amount == D("1000") and uow.commits == 1
    await svc.create(user.id, data(acc, income, type="income"))
    t = await svc.create(user.id, data(acc, None, type="transfer", category_id=None, transfer_account_id=acc2.id))
    assert t.transfer_account_id == acc2.id
    assert len(uow.transactions.all()) == 3


@pytest.mark.parametrize(
    "over",
    [
        {"amount": D("0")},
        {"amount": D("-1")},
        {"type": "income"},  # categoría de gasto
        {"category_id": None},
        {"transfer_account_id": "ACC2"},
        {"type": "transfer", "category_id": None, "transfer_account_id": None},
        {"type": "transfer", "category_id": None, "transfer_account_id": "ACC1"},
        {"type": "transfer", "transfer_account_id": "ACC2"},  # transferencia con categoría
    ],
)
async def test_business_rule_violations(env, over):
    uow, user, acc, acc2, expense, income = env
    over = {k: (acc.id if v == "ACC1" else acc2.id if v == "ACC2" else v) for k, v in over.items()}
    with pytest.raises(BusinessRuleError):
        await TransactionService(uow).create(user.id, data(acc, expense, **over))
    assert uow.transactions.all() == []


async def test_archived_account_rejects_new_but_not_edits(env):
    uow, user, acc, acc2, expense, _ = env
    svc = TransactionService(uow)
    tx = await svc.create(user.id, data(acc, expense))
    acc.archived = True
    await uow.accounts.update(acc)
    with pytest.raises(BusinessRuleError):
        await svc.create(user.id, data(acc, expense))
    updated = await svc.update(user.id, tx.id, {"amount": D("2000")})  # misma cuenta archivada: se permite
    assert updated.amount == D("2000")
    with pytest.raises(BusinessRuleError):
        await svc.update(user.id, tx.id, {"account_id": acc.id, "transfer_account_id": None, "type": "transfer", "category_id": None})


async def test_unknown_refs_are_not_found(env):
    uow, user, acc, _, expense, _ = env
    from uuid import uuid4

    svc = TransactionService(uow)
    with pytest.raises(NotFoundError):
        await svc.create(user.id, data(acc, expense, category_id=uuid4()))
    with pytest.raises(NotFoundError):
        await svc.create(user.id, data(acc, expense, account_id=uuid4()))
    with pytest.raises(NotFoundError):
        await svc.get(user.id, uuid4())


# ---- presupuestos ----
async def test_budget_status_flow(env):
    uow, user, acc, _, expense, income = env
    bsvc, tsvc = BudgetService(uow), TransactionService(uow)
    month = date(2026, 10, 1)
    st = await bsvc.create(user.id, {"category_id": expense.id, "month": month, "amount_limit": D("600000")})
    assert st.status == BudgetState.OK and st.spent == 0 and st.alert_threshold == D("0.80")

    await tsvc.create(user.id, data(acc, expense, amount=D("510000")))
    # gasto de otro mes no cuenta
    await tsvc.create(user.id, data(acc, expense, amount=D("999999"), date=date(2026, 9, 30)))
    [s] = await bsvc.list(user.id, month)
    assert (s.spent, s.remaining, s.percent, s.status) == (D("510000"), D("90000"), 85.0, BudgetState.WARNING)

    await tsvc.create(user.id, data(acc, expense, amount=D("100000")))
    [s] = await bsvc.list(user.id, month)
    assert s.status == BudgetState.EXCEEDED

    with pytest.raises(ConflictError):
        await bsvc.create(user.id, {"category_id": expense.id, "month": month, "amount_limit": D("1")})
    with pytest.raises(BusinessRuleError):
        await bsvc.create(user.id, {"category_id": income.id, "month": month, "amount_limit": D("1")})
    with pytest.raises(BusinessRuleError):
        await bsvc.create(user.id, {"category_id": expense.id, "month": date(2026, 11, 1), "amount_limit": D("0")})


async def test_budget_copy_skips_existing(env):
    uow, user, _, _, expense, _ = env
    other = Category(user_id=user.id, name="Ocio", kind=CategoryKind.EXPENSE)
    await uow.categories.add(other)
    svc = BudgetService(uow)
    m1, m2 = date(2026, 9, 1), date(2026, 10, 1)
    await svc.create(user.id, {"category_id": expense.id, "month": m1, "amount_limit": D("100")})
    await svc.create(user.id, {"category_id": other.id, "month": m1, "amount_limit": D("200")})
    await svc.create(user.id, {"category_id": other.id, "month": m2, "amount_limit": D("999")})
    created = await svc.copy(user.id, m1, m2)
    assert [c.category_id for c in created] == [expense.id]
    assert len(await svc.list(user.id, m2)) == 2


# ---- recurrentes ----
async def make_rule(uow, user, acc, cat, **over):
    base = {"type": "expense", "amount": D("39900"), "account_id": acc.id, "category_id": cat.id,
            "note": "Netflix", "frequency": "monthly", "interval": 1, "start_date": date(2026, 1, 31)}
    base.update(over)
    return await RecurringService(uow).create(user.id, base)


async def test_recurring_run_generates_and_is_idempotent(env):
    uow, user, acc, _, expense, _ = env
    rule = await make_rule(uow, user, acc, expense)
    assert rule.next_run_date == date(2026, 1, 31)
    svc = RecurringService(uow)
    assert await svc.run(user.id, TODAY) == 9  # ene..sep (oct 31 aún no)
    dates = sorted(t.date for t in uow.transactions.all())
    assert dates[:3] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert all(t.recurring_id == rule.id for t in uow.transactions.all())
    assert (await uow.recurring.get(user.id, rule.id)).next_run_date == date(2026, 10, 31)
    assert await svc.run(user.id, TODAY) == 0  # idempotente
    assert len(uow.transactions.all()) == 9
    assert await svc.run(user.id, date(2026, 10, 31)) == 1


async def test_recurring_end_date_deactivates(env):
    uow, user, acc, _, expense, _ = env
    rule = await make_rule(uow, user, acc, expense, frequency="weekly", start_date=date(2026, 10, 1),
                           end_date=date(2026, 10, 10))
    assert await RecurringService(uow).run(user.id, TODAY) == 2  # 1 y 8 de octubre
    r = await uow.recurring.get(user.id, rule.id)
    assert r.active is False


async def test_recurring_future_start_and_upcoming(env):
    uow, user, acc, _, expense, _ = env
    await make_rule(uow, user, acc, expense, frequency="weekly", start_date=TODAY + timedelta(days=3))
    svc = RecurringService(uow)
    assert await svc.run(user.id, TODAY) == 0
    items = await svc.upcoming(user.id, 15, TODAY)
    assert [i.date for i in items] == [TODAY + timedelta(days=3), TODAY + timedelta(days=10)]


async def test_recurring_validation(env):
    uow, user, acc, _, expense, income = env
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, income)  # categoría de ingreso en un gasto
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, expense, amount=D("0"))
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, expense, end_date=date(2025, 1, 1))


# ---- metas ----
async def test_goal_contributions_cannot_go_negative(env):
    uow, user, *_ = env
    uow.users.items[user.id].timezone = "America/Bogota"
    svc = GoalService(uow)
    g = await svc.create(user.id, {"name": "Viaje", "target_amount": D("1000")})
    assert g.saved == 0 and g.monthly_needed is None
    await svc.add_contribution(user.id, g.id, {"amount": D("400")})
    with pytest.raises(BusinessRuleError):
        await svc.add_contribution(user.id, g.id, {"amount": D("-500")})
    await svc.add_contribution(user.id, g.id, {"amount": D("-100")})
    assert (await svc.get(user.id, g.id)).saved == D("300")
    with pytest.raises(BusinessRuleError):
        await svc.add_contribution(user.id, g.id, {"amount": D("0")})
    contribs = await svc.contributions(user.id, g.id)
    big = next(c for c in contribs if c.amount == D("400"))
    with pytest.raises(BusinessRuleError):
        await svc.delete_contribution(user.id, g.id, big.id)  # dejaría -100
    await svc.add_contribution(user.id, g.id, {"amount": D("700")})
    assert (await svc.get(user.id, g.id)).completed is True


# ---- recurrentes por días del mes ----
async def test_quincenal_paycheck_run_idempotent_and_weekend_adjust(env):
    uow, user, acc, _, _, income = env
    svc = RecurringService(uow)
    rule = await make_rule(uow, user, acc, income, type="income", amount=D("1000000"), frequency="monthly_days",
                           days_of_month="L,15", interval=5, start_date=date(2026, 9, 1), is_paycheck=True,
                           weekend_adjust="previous_business_day")
    assert (rule.days_of_month, rule.interval, rule.next_run_date) == ("15,L", 1, date(2026, 9, 15))
    # 15/9, 30/9, 15/10, 31/10 (sáb -> vie 30/10), 15/11 (dom -> vie 13/11)
    assert await svc.run(user.id, date(2026, 11, 14)) == 5
    assert sorted(t.date for t in uow.transactions.all()) == [
        date(2026, 9, 15), date(2026, 9, 30), date(2026, 10, 15), date(2026, 10, 30), date(2026, 11, 13)]
    assert (await uow.recurring.get(user.id, rule.id)).next_run_date == date(2026, 11, 30)
    assert await svc.run(user.id, date(2026, 11, 14)) == 0
    up = await svc.upcoming(user.id, 40, date(2026, 11, 14))
    assert [(i.date, i.is_paycheck) for i in up] == [(date(2026, 11, 30), True), (date(2026, 12, 15), True)]


async def test_weekend_adjust_runs_on_effective_date_not_nominal(env):
    uow, user, acc, _, _, income = env
    svc = RecurringService(uow)
    await make_rule(uow, user, acc, income, type="income", frequency="monthly_days", days_of_month="15",
                    start_date=date(2026, 11, 1), weekend_adjust="previous_business_day")
    assert await svc.run(user.id, date(2026, 11, 12)) == 0
    assert await svc.run(user.id, date(2026, 11, 13)) == 1  # nominal domingo 15, vence el viernes 13


async def test_monthly_days_validation(env):
    uow, user, acc, _, expense, income = env
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, expense, frequency="monthly_days")  # falta days_of_month
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, expense, days_of_month="15")  # con frecuencia monthly
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, expense, frequency="monthly_days", days_of_month="32")
    with pytest.raises(BusinessRuleError):
        await make_rule(uow, user, acc, expense, is_paycheck=True)  # sueldo solo en ingresos


async def test_update_recomputes_next_run_for_monthly_days(env):
    uow, user, acc, _, _, income = env
    svc = RecurringService(uow)
    rule = await make_rule(uow, user, acc, income, type="income", start_date=date(2026, 1, 1))
    r = await svc.update(user.id, rule.id, {"frequency": "monthly_days", "days_of_month": "15,L"}, today=date(2026, 10, 16))
    assert r.next_run_date == date(2026, 10, 31) and r.interval == 1
    r = await svc.update(user.id, rule.id, {"frequency": "weekly"}, today=date(2026, 10, 16))
    assert r.days_of_month is None  # al salir de monthly_days se limpian los días
