from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.application.budgets import BudgetService
from app.application.ports import today_in
from app.application.recurring import RecurringService
from app.domain.entities import (
    Account,
    BudgetStatus,
    CategoryTotal,
    Transaction,
    UpcomingItem,
)
from app.domain.enums import BudgetState, TransactionType
from app.domain.exceptions import BusinessRuleError
from app.domain.repositories import UnitOfWork
from app.domain.pay_periods import (
    PayPeriod,
    Payday,
    PeriodSpan,
    build_spans,
    merge_pay_dates,
    paydays,
    period_metrics,
)
from app.domain.rules import add_months, first_of_month, last_of_month

ZERO = Decimal("0.00")


@dataclass(kw_only=True)
class CategoryReportRow:
    category_id: UUID
    name: str
    color: str
    icon: str
    total: Decimal
    percent: float
    count: int


@dataclass(kw_only=True)
class TrendRow:
    month: str
    income: Decimal
    expense: Decimal
    net: Decimal


@dataclass(kw_only=True)
class Dashboard:
    period_from: date
    period_to: date
    total_balance: Decimal
    income: Decimal
    expense: Decimal
    net: Decimal
    savings_rate: float
    by_category: list[CategoryReportRow]
    monthly_trend: list[TrendRow]
    accounts: list[Account]
    budgets_at_risk: list[BudgetStatus]
    upcoming_recurring: list[UpcomingItem]
    recent_transactions: list[Transaction]
    current_pay_period: PayPeriod | None = None
    previous_pay_period: PayPeriod | None = None
    next_payday: Payday | None = None


def _percent_rows(totals: list[CategoryTotal]) -> list[CategoryReportRow]:
    grand = sum((t.total for t in totals), ZERO)
    return [
        CategoryReportRow(
            category_id=t.category_id, name=t.name, color=t.color, icon=t.icon, total=t.total,
            percent=round(float(t.total / grand * 100), 1) if grand > 0 else 0.0, count=t.count,
        )
        for t in totals
    ]


class ReportService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _today(self, user_id: UUID) -> date:
        user = await self.uow.users.get(user_id)
        return today_in(user.timezone if user else "UTC")

    @staticmethod
    def _check_range(start: date, end: date) -> None:
        if start > end:
            raise BusinessRuleError("La fecha inicial no puede ser posterior a la final")

    async def _trend(self, user_id: UUID, months: int, end_month: date) -> list[TrendRow]:
        start = add_months(first_of_month(end_month), -(months - 1))
        found = {
            m.month: m for m in await self.uow.transactions.monthly_totals(
                user_id, start, last_of_month(end_month)
            )
        }
        rows = []
        for i in range(months):
            m = add_months(start, i)
            t = found.get(m)
            inc, exp = (t.income, t.expense) if t else (ZERO, ZERO)
            rows.append(TrendRow(month=m.strftime("%Y-%m"), income=inc, expense=exp, net=inc - exp))
        return rows

    async def trend(self, user_id: UUID, months: int, end_month: date) -> list[TrendRow]:
        return await self._trend(user_id, months, end_month)

    async def today(self, user_id: UUID) -> date:
        return await self._today(user_id)

    async def period(self, user_id: UUID, span: PeriodSpan, today: date) -> PayPeriod:
        return await self._period(user_id, span, today)

    async def by_category(
        self, user_id: UUID, start: date, end: date, type: TransactionType
    ) -> list[CategoryReportRow]:
        self._check_range(start, end)
        if type == TransactionType.TRANSFER:
            raise BusinessRuleError("El reporte solo admite gastos o ingresos")
        return _percent_rows(await self.uow.transactions.category_totals(user_id, start, end, type))

    async def monthly_trend(self, user_id: UUID, months: int) -> list[TrendRow]:
        today = await self._today(user_id)
        return await self._trend(user_id, months, today)

    async def _period(self, user_id: UUID, span: PeriodSpan, today: date) -> PayPeriod:
        tx = self.uow.transactions
        income, expense = await tx.totals(user_id, span.start, span.end)  # sin transferencias
        salary = await tx.salary_total(user_id, span.start, span.end)
        period = period_metrics(span, today, income, expense, salary)
        period.by_category = _percent_rows(
            await tx.category_totals(user_id, span.start, span.end, TransactionType.EXPENSE)
        )
        return period

    async def pay_dates(self, user_id: UUID, today: date) -> tuple[list[date], list[Payday]]:
        """(fechas de pago, próximos pagos de las reglas).

        Fechas = sueldos reales ya registrados (<= hoy) + fechas efectivas futuras del calendario de
        las reglas de sueldo (> hoy), sin duplicados y fusionando las que quedan a 3 días o menos."""
        rule_paydays = paydays(await self.uow.recurring.list(user_id), today)
        real = await self.uow.transactions.salary_dates(user_id, today)
        dates = merge_pay_dates(real, [p.date for p in rule_paydays], today)
        return dates, [p for p in rule_paydays if p.date > today]

    async def pay_periods(self, user_id: UUID, count: int) -> list[PayPeriod]:
        """Quincenas de pago de la más reciente (la que contiene hoy) a la más antigua."""
        today = await self._today(user_id)
        pay_dates, _ = await self.pay_dates(user_id, today)
        return [await self._period(user_id, s, today) for s in build_spans(pay_dates, today, count)]

    async def dashboard(self, user_id: UUID, start: date | None, end: date | None) -> Dashboard:
        today = await self._today(user_id)
        if start is None:
            start = first_of_month(end or today)
        end = end or last_of_month(start)
        self._check_range(start, end)
        tx = self.uow.transactions
        accounts = await self.uow.accounts.list(user_id, include_archived=False)
        income, expense = await tx.totals(user_id, start, end)
        budgets = await BudgetService(self.uow).list(user_id, first_of_month(end))
        upcoming = await RecurringService(self.uow).upcoming(user_id, 7, today)
        pay_dates, upcoming_paydays = await self.pay_dates(user_id, today)
        spans = build_spans(pay_dates, today, 2)
        return Dashboard(
            period_from=start,
            period_to=end,
            total_balance=sum((a.balance for a in accounts), ZERO),
            income=income,
            expense=expense,
            net=income - expense,
            savings_rate=round(float((income - expense) / income * 100), 1) if income > 0 else 0.0,
            by_category=_percent_rows(
                await tx.category_totals(user_id, start, end, TransactionType.EXPENSE)
            ),
            monthly_trend=await self._trend(user_id, 6, end),
            accounts=accounts,
            budgets_at_risk=[b for b in budgets if b.status != BudgetState.OK],
            upcoming_recurring=upcoming,
            recent_transactions=await tx.recent(user_id, 5),
            current_pay_period=await self._period(user_id, spans[0], today),
            previous_pay_period=await self._period(user_id, spans[1], today),
            next_payday=upcoming_paydays[0] if upcoming_paydays else None,
        )

    async def export_csv(self, user_id: UUID, start: date | None, end: date | None) -> tuple[str, date, date]:
        today = await self._today(user_id)
        if start is None:
            start = first_of_month(end or today)
        end = end or last_of_month(start)
        self._check_range(start, end)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        w.writerow(["fecha", "tipo", "monto", "cuenta", "categoria", "cuenta_destino", "nota"])
        labels = {"income": "ingreso", "expense": "gasto", "transfer": "transferencia"}
        for r in await self.uow.transactions.export_rows(user_id, start, end):
            w.writerow([
                r.date.isoformat(), labels[r.type.value], f"{r.amount:.2f}", r.account,
                r.category or "", r.transfer_account or "", _safe(r.note),
            ])
        return "﻿" + buf.getvalue(), start, end


def _safe(text: str | None) -> str:
    """Evita inyección de fórmulas al abrir el CSV en Excel/Sheets."""
    if not text:
        return ""
    return "'" + text if text[0] in "=+-@\t\r" else text
