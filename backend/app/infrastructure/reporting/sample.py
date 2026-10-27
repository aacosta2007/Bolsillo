"""Reporte de ejemplo (sin base de datos) para revisar el diseño del PDF: `python -m app.cli sample-report`.

Reproduce las cifras de `docs/design/v2/PDF1-3.dc.html` y pasa por las mismas funciones de dominio
(métricas, observaciones y texto de cierre) que usa el reporte real."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid5, NAMESPACE_DNS

from app.domain.entities import BudgetStatus, CategoryTotal, DailyTotal, TopExpense
from app.domain.insights import generate_insights, next_month_outlook
from app.domain.monthly_report import (
    GoalReport,
    MonthlyReport,
    TrendPoint,
    build_category_changes,
    build_daily,
    build_summary,
    goal_status,
    savings_rate,
    summarize_budgets,
)
from app.domain.pay_periods import PeriodSource, PeriodSpan, period_metrics
from app.domain.rules import budget_status, goal_percent, monthly_needed

D = Decimal


def _id(name: str) -> UUID:
    return uuid5(NAMESPACE_DNS, f"bolsillo.sample.{name}")


def sample_report() -> MonthlyReport:
    month, today = date(2026, 10, 1), date(2026, 11, 1)
    cat = {n: _id(n) for n in ("Hogar/Arriendo", "Comida", "Servicios", "Transporte", "Entretenimiento", "Otros", "Salario", "Freelance")}

    def ct(name: str, total: int, count: int) -> CategoryTotal:
        return CategoryTotal(category_id=cat[name], name=name, color="#64748b", icon="circle", total=D(total), count=count)

    expenses = [
        ("Hogar/Arriendo", 700000, 1, 700000), ("Comida", 452300, 14, 383300), ("Servicios", 182000, 3, 195000),
        ("Transporte", 160000, 8, 160000), ("Entretenimiento", 120000, 4, 96000), ("Otros", 70000, 5, 55700),
    ]
    expense_cats = build_category_changes(
        [ct(n, t, c) for n, t, c, _ in expenses], [ct(n, p, 1) for n, _, _, p in expenses]
    )
    income_cats = build_category_changes(
        [ct("Salario", 2000000, 2), ct("Freelance", 350000, 1)], [ct("Salario", 2000000, 2)], flag_new=True
    )
    trend_src = [("2026-05", 2000000, 1750000), ("2026-06", 2000000, 1820000), ("2026-07", 2100000, 1600000),
                 ("2026-08", 2000000, 2020000), ("2026-09", 2000000, 1590000), ("2026-10", 2350000, 1684300)]
    trend = [
        TrendPoint(month=m, income=D(i), expense=D(e), net=D(i - e), savings_rate=savings_rate(D(i), D(e)))
        for m, i, e in trend_src
    ]
    values = [12, 35, 0, 22, 715, 15, 40, 18, 9, 55, 0, 138, 20, 30, 92, 25, 14, 60, 0, 47, 10, 33, 18, 95, 12, 28, 0, 170, 22, 96, 9]
    rows = [
        DailyTotal(date=date(2026, 10, i + 1), income=D(0), expense=D(v * 1000), paycheck_income=D(1000000 if i + 1 in (15, 30) else 0))
        for i, v in enumerate(values) if v or i + 1 in (15, 30)
    ]
    daily, stats = build_daily(month, date(2026, 10, 31), rows)

    spans = [
        (PeriodSpan(start=date(2026, 9, 30), end=date(2026, 10, 14), source=PeriodSource.PAYCHECK), 1000000, 902100),
        (PeriodSpan(start=date(2026, 10, 15), end=date(2026, 10, 29), source=PeriodSource.PAYCHECK), 1350000, 1102200),
        (PeriodSpan(start=date(2026, 10, 30), end=date(2026, 11, 14), source=PeriodSource.PAYCHECK), 1000000, 98000),
    ]
    periods = [period_metrics(s, today, D(i), D(e), D(1000000)) for s, i, e in spans]

    budgets = []
    for name, spent, limit in (
        ("Hogar/Arriendo", 700000, 750000), ("Comida", 452300, 600000), ("Transporte", 160000, 250000),
        ("Servicios", 182000, 250000), ("Entretenimiento", 120000, 100000),
    ):
        remaining, pct, state = budget_status(D(limit), D(spent), D("0.80"))
        budgets.append(BudgetStatus(
            id=_id(f"budget.{name}"), category_id=cat[name], month=month, amount_limit=D(limit),
            alert_threshold=D("0.80"), spent=D(spent), remaining=remaining, percent=pct, status=state,
        ))

    goals = []
    for name, color, saved, target, contributed, target_date in (
        ("Viaje a Cartagena", "#0F5E55", 1050000, 3000000, 300000, date(2027, 6, 1)),
        ("Fondo de emergencia", "#2563EB", 2400000, 6000000, 0, date(2027, 12, 1)),
        ("Portátil nuevo", "#C2410C", 3100000, 3500000, 200000, date(2026, 12, 1)),
    ):
        needed = monthly_needed(D(target), D(saved), target_date, today)
        goals.append(GoalReport(
            id=_id(f"goal.{name}"), name=name, color=color, target_amount=D(target), saved=D(saved),
            percent=goal_percent(D(target), D(saved)), contributed_this_month=D(contributed), monthly_needed=needed,
            status=goal_status(target_amount=D(target), saved=D(saved), target_date=target_date,
                               monthly_needed=needed, contributed_this_month=D(contributed)),
            target_date=target_date,
        ))

    top = [
        ("Arriendo", "Hogar/Arriendo", date(2026, 10, 5), 700000), ("Plan celular", "Servicios", date(2026, 10, 28), 170000),
        ("Mercado D1", "Comida", date(2026, 10, 12), 138400), ("Concierto", "Entretenimiento", date(2026, 10, 24), 95000),
        ("Recarga Cívica", "Transporte", date(2026, 10, 15), 80000),
    ]
    report = MonthlyReport(
        month=month, is_partial=False, generated_at=datetime(2026, 11, 1, 13, 0, tzinfo=timezone.utc), currency="COP",
        summary=build_summary(D(2350000), D(1684300), D(2000000), D(1590000)),
        expense_by_category=expense_cats, income_by_category=income_cats,
        top_expenses=[
            TopExpense(transaction_id=_id(f"tx.{i}"), date=d, note=n, category=c, account="Bancolombia", amount=D(a))
            for i, (n, c, d, a) in enumerate(top)
        ],
        daily=daily, daily_stats=stats, pay_periods=periods, budgets=budgets, budgets_summary=summarize_budgets(budgets),
        goals=goals, trend=trend, category_names={cat[n]: n for n in cat}, timezone="America/Bogota",
    )
    report.insights = generate_insights(report)
    report.outlook = next_month_outlook(report)
    return report
