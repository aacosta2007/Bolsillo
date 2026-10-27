"""Reporte mensual: orquesta repositorios y servicios existentes y delega las métricas al dominio."""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from app.application.budgets import BudgetService
from app.application.ports import today_in
from app.application.reports import ReportService
from app.domain.entities import ZERO, Goal
from app.domain.enums import TransactionType
from app.domain.exceptions import BusinessRuleError
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
from app.domain.pay_periods import PayPeriod, build_spans
from app.domain.repositories import UnitOfWork
from app.domain.rules import add_months, first_of_month, goal_percent, last_of_month, monthly_needed

TOP_EXPENSES = 5
TREND_MONTHS = 6


class MonthlyReportService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.reports = ReportService(uow)

    async def build(self, user_id: UUID, month: date) -> MonthlyReport:
        month = first_of_month(month)
        user = await self.uow.users.get(user_id)
        today = today_in(user.timezone if user else "UTC")
        current_month = first_of_month(today)
        if month > current_month:
            raise BusinessRuleError("No se puede generar el reporte de un mes futuro")
        is_partial = month == current_month
        month_end = last_of_month(month)
        last_day = today if is_partial else month_end
        prev_month = add_months(month, -1)
        prev_end = last_of_month(prev_month)
        tx = self.uow.transactions

        trend_rows = await self.reports.trend(user_id, TREND_MONTHS, month)
        cur, prev = trend_rows[-1], trend_rows[-2]
        summary = build_summary(cur.income, cur.expense, prev.income, prev.expense)

        expense_cats = build_category_changes(
            await tx.category_totals(user_id, month, month_end, TransactionType.EXPENSE),
            await tx.category_totals(user_id, prev_month, prev_end, TransactionType.EXPENSE),
        )
        income_cats = build_category_changes(
            await tx.category_totals(user_id, month, month_end, TransactionType.INCOME),
            await tx.category_totals(user_id, prev_month, prev_end, TransactionType.INCOME),
            flag_new=True,
        )
        top_expenses = await tx.top_expenses(user_id, month, month_end, TOP_EXPENSES)
        daily, daily_stats = build_daily(month, last_day, await tx.daily_totals(user_id, month, last_day))

        pay_periods = await self._pay_periods(user_id, month, month_end, today, is_partial)
        budgets = await BudgetService(self.uow).list(user_id, month)
        category_names = {c.id: c.name for c in await self.uow.categories.list(user_id, None)}
        goals = await self._goals(user_id, month, month_end, min(today, month_end))

        report = MonthlyReport(
            month=month,
            is_partial=is_partial,
            generated_at=datetime.now(timezone.utc),
            currency=user.currency if user else "COP",
            summary=summary,
            expense_by_category=expense_cats,
            income_by_category=income_cats,
            top_expenses=top_expenses,
            daily=daily,
            daily_stats=daily_stats,
            pay_periods=pay_periods,
            budgets=budgets,
            budgets_summary=summarize_budgets(budgets),
            goals=goals,
            trend=[
                TrendPoint(
                    month=t.month, income=t.income, expense=t.expense, net=t.net,
                    savings_rate=savings_rate(t.income, t.expense),
                )
                for t in trend_rows
            ],
            category_names=category_names,
            timezone=user.timezone if user else "UTC",
        )
        report.insights = generate_insights(report)
        report.outlook = next_month_outlook(report)
        return report

    async def _pay_periods(
        self, user_id: UUID, month: date, month_end: date, today: date, is_partial: bool
    ) -> list[PayPeriod]:
        """Quincenas de pago que se cruzan con el mes, en orden cronológico."""
        reference = today if is_partial else month_end
        pay_dates, _ = await self.reports.pay_dates(user_id, today)
        count = 8
        while True:
            spans = build_spans(pay_dates, reference, count)
            if spans[-1].start <= month or count >= 96:
                break
            count *= 2
        overlapping = [s for s in spans if s.end >= month and s.start <= month_end]
        return [await self.reports.period(user_id, s, today) for s in reversed(overlapping)]

    async def _goals(self, user_id: UUID, month: date, month_end: date, ref_today: date) -> list[GoalReport]:
        """Metas con su ahorro a fin de mes (aportes posteriores no cuentan) y lo aportado en el mes."""
        goals = await self.uow.goals.list(user_id)
        totals = await self.uow.goals.contribution_totals(user_id, month, month_end)
        out: list[GoalReport] = []
        for g in goals:
            t = totals.get(g.id)
            in_range, after = (t.in_range, t.after) if t else (ZERO, ZERO)
            saved = max(g.saved - after, ZERO)
            if _created_after(g, month_end) and saved == 0 and in_range == 0:
                continue  # la meta aún no existía
            needed = monthly_needed(g.target_amount, saved, g.target_date, ref_today)
            out.append(
                GoalReport(
                    id=g.id, name=g.name, color=g.color, target_amount=g.target_amount, saved=saved,
                    percent=goal_percent(g.target_amount, saved),
                    contributed_this_month=in_range, monthly_needed=needed,
                    status=goal_status(
                        target_amount=g.target_amount, saved=saved, target_date=g.target_date,
                        monthly_needed=needed, contributed_this_month=in_range,
                    ),
                    target_date=g.target_date,
                )
            )
        return out


def _created_after(g: Goal, day: date) -> bool:
    return g.created_at.date() > day

