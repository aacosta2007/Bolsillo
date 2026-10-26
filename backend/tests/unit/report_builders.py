"""Constructores de MonthlyReport para pruebas unitarias (sin base de datos)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid5, NAMESPACE_DNS

from app.domain.entities import BudgetStatus, CategoryTotal, DailyTotal
from app.domain.insights import generate_insights, next_month_outlook
from app.domain.monthly_report import (
    GoalReport,
    MonthlyReport,
    TrendPoint,
    build_category_changes,
    build_daily,
    build_summary,
    savings_rate,
    summarize_budgets,
)
from app.domain.pay_periods import PayPeriod, PeriodSource, PeriodSpan, period_metrics
from app.domain.rules import budget_status

D = Decimal
MONTH = date(2026, 10, 1)
_NAMES: dict[UUID, str] = {}


def cid(name: str) -> UUID:
    return uuid5(NAMESPACE_DNS, f"bolsillo.test.{name}")


def totals(rows: list[tuple[str, int]]) -> list[CategoryTotal]:
    return [
        CategoryTotal(category_id=cid(n), name=n, color="#64748b", icon="circle", total=D(t), count=2)
        for n, t in rows
    ]


def budget(name: str, spent: int, limit: int, threshold: str = "0.80") -> BudgetStatus:
    remaining, pct, state = budget_status(D(limit), D(spent), D(threshold))
    _NAMES[cid(name)] = name
    return BudgetStatus(
        id=cid(f"b.{name}"), category_id=cid(name), month=MONTH, amount_limit=D(limit),
        alert_threshold=D(threshold), spent=D(spent), remaining=remaining, percent=pct, status=state,
    )


def period(start: date, end: date, income: int, expense: int, today: date = date(2026, 11, 20)) -> PayPeriod:
    span = PeriodSpan(start=start, end=end, source=PeriodSource.PAYCHECK)
    return period_metrics(span, today, D(income), D(expense))


def goal(
    name: str = "Viaje", *, saved: int = 500000, target: int = 3000000, contributed: int = 0,
    needed: int | None = 250000, target_date: date | None = date(2027, 6, 1), status=None,
) -> GoalReport:
    from app.domain.monthly_report import goal_status

    needed_d = D(needed) if needed is not None else None
    return GoalReport(
        id=cid(f"g.{name}"), name=name, color="#0F5E55", target_amount=D(target), saved=D(saved),
        percent=round(saved / target * 100, 1), contributed_this_month=D(contributed), monthly_needed=needed_d,
        status=status or goal_status(
            target_amount=D(target), saved=D(saved), target_date=target_date,
            monthly_needed=needed_d, contributed_this_month=D(contributed),
        ),
        target_date=target_date,
    )


def make_report(
    *,
    income: int = 2000000,
    expense: int = 1500000,
    prev_income: int = 2000000,
    prev_expense: int = 1500000,
    expense_cats: list[tuple[str, int, int]] | None = None,  # (nombre, total, anterior)
    income_cats: list[tuple[str, int, int]] | None = None,
    prior_trend: list[tuple[int, int]] | None = None,  # 4 meses previos al anterior: (ingreso, gasto)
    budgets: list[BudgetStatus] | None = None,
    periods: list[PayPeriod] | None = None,
    goals: list[GoalReport] | None = None,
    spend_days: list[int] | None = None,  # días del mes con gasto
    is_partial: bool = False,
    last_day: int = 31,
) -> MonthlyReport:
    expense_cats = expense_cats if expense_cats is not None else [("Comida", expense, prev_expense)]
    income_cats = income_cats if income_cats is not None else [("Salario", income, prev_income)]
    prior = prior_trend if prior_trend is not None else [(prev_income, prev_expense)] * 4
    trend_src = [*prior, (prev_income, prev_expense), (income, expense)]
    months = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    trend = [
        TrendPoint(month=m, income=D(i), expense=D(e), net=D(i - e), savings_rate=savings_rate(D(i), D(e)))
        for m, (i, e) in zip(months, trend_src)
    ]
    days = spend_days if spend_days is not None else list(range(1, last_day + 1))
    per_day = D(expense) / max(len(days), 1)
    rows = [DailyTotal(date=date(2026, 10, d), income=D(0), expense=per_day.quantize(D("0.01")), paycheck_income=D(0)) for d in days]
    daily, stats = build_daily(MONTH, date(2026, 10, last_day), rows)
    budgets = budgets or []
    report = MonthlyReport(
        month=MONTH, is_partial=is_partial, generated_at=datetime(2026, 11, 1, 13, 0, tzinfo=timezone.utc),
        currency="COP",
        summary=build_summary(D(income), D(expense), D(prev_income), D(prev_expense)),
        expense_by_category=build_category_changes(
            totals([(n, t) for n, t, _ in expense_cats if t]), totals([(n, p) for n, _, p in expense_cats if p])
        ),
        income_by_category=build_category_changes(
            totals([(n, t) for n, t, _ in income_cats if t]), totals([(n, p) for n, _, p in income_cats if p]),
            flag_new=True,
        ),
        top_expenses=[], daily=daily, daily_stats=stats, pay_periods=periods or [], budgets=budgets,
        budgets_summary=summarize_budgets(budgets), goals=goals or [], trend=trend,
        category_names={**_NAMES, **{cid(n): n for n, *_ in [*expense_cats, *income_cats]}},
        timezone="America/Bogota",
    )
    report.insights = generate_insights(report)
    report.outlook = next_month_outlook(report)
    return report
