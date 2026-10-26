"""Modelo y métricas puras del reporte mensual (sin I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.entities import BudgetStatus, CategoryTotal, DailyTotal, TopExpense
from app.domain.enums import BudgetState
from app.domain.pay_periods import PayPeriod

ZERO = Decimal("0.00")
HUNDRED = Decimal(100)


class GoalStatus(StrEnum):
    ON_TRACK = "on_track"
    BEHIND = "behind"
    COMPLETED = "completed"
    NO_TARGET_DATE = "no_target_date"


class InsightKind(StrEnum):
    CATEGORY_UP = "category_up"
    CATEGORY_DOWN = "category_down"
    SAVINGS_RECORD = "savings_record"
    NEW_INCOME = "new_income"
    BUDGET_EXCEEDED = "budget_exceeded"
    PAY_PERIOD_SHORT = "pay_period_short"
    NO_SPEND_DAYS = "no_spend_days"
    SAVINGS_RATE = "savings_rate"


class Tone(StrEnum):
    POSITIVE = "positive"
    WARNING = "warning"
    NEUTRAL = "neutral"


@dataclass(kw_only=True)
class PeriodTotals:
    income: Decimal
    expense: Decimal
    net: Decimal
    savings_rate: float


@dataclass(kw_only=True)
class Summary:
    income: Decimal
    expense: Decimal
    net: Decimal
    savings_rate: float
    prev: PeriodTotals
    income_change_pct: float | None
    expense_change_pct: float | None
    net_change_pct: float | None


@dataclass(kw_only=True)
class CategoryChange:
    category_id: UUID
    name: str
    color: str
    icon: str
    total: Decimal
    prev_total: Decimal
    change_pct: float | None
    percent: float
    count: int
    is_new: bool = False  # solo se usa en ingresos


@dataclass(kw_only=True)
class DailyRow:
    date: date
    expense: Decimal
    income: Decimal
    is_payday: bool


@dataclass(kw_only=True)
class DailyStats:
    max_day: date | None
    max_day_expense: Decimal
    avg_daily_expense: Decimal
    no_spend_days: int


@dataclass(kw_only=True)
class BudgetsSummary:
    ok: int
    warning: int
    exceeded: int


@dataclass(kw_only=True)
class GoalReport:
    id: UUID
    name: str
    color: str
    target_amount: Decimal
    saved: Decimal
    percent: float
    contributed_this_month: Decimal
    monthly_needed: Decimal | None
    status: GoalStatus
    target_date: date | None = None  # no sale en el JSON; la usa el texto "para el próximo mes"


@dataclass(kw_only=True)
class TrendPoint:
    month: str
    income: Decimal
    expense: Decimal
    net: Decimal
    savings_rate: float


@dataclass(kw_only=True)
class Insight:
    kind: InsightKind
    tone: Tone
    text: str


@dataclass(kw_only=True)
class MonthlyReport:
    month: date  # primer día del mes
    is_partial: bool
    generated_at: datetime
    currency: str
    summary: Summary
    expense_by_category: list[CategoryChange]
    income_by_category: list[CategoryChange]
    top_expenses: list[TopExpense]
    daily: list[DailyRow]
    daily_stats: DailyStats
    pay_periods: list[PayPeriod]
    budgets: list[BudgetStatus]
    budgets_summary: BudgetsSummary
    goals: list[GoalReport]
    trend: list[TrendPoint]
    insights: list[Insight] = field(default_factory=list)
    # Extras para el PDF (no forman parte del JSON del contrato)
    outlook: str = ""
    category_names: dict[UUID, str] = field(default_factory=dict)
    timezone: str = "UTC"


# ---------- Métricas ----------
def savings_rate(income: Decimal, expense: Decimal) -> float:
    """(ingresos - gastos) / ingresos × 100 con 1 decimal; 0 si no hay ingresos."""
    return round(float((income - expense) / income * 100), 1) if income > 0 else 0.0


def change_pct(current: Decimal, previous: Decimal) -> float | None:
    """(actual - anterior) / anterior × 100 con 1 decimal; None si el anterior es 0."""
    if previous == 0:
        return None
    return round(float((current - previous) / abs(previous) * 100), 1)


def period_totals(income: Decimal, expense: Decimal) -> PeriodTotals:
    return PeriodTotals(
        income=income, expense=expense, net=income - expense, savings_rate=savings_rate(income, expense)
    )


def build_summary(income: Decimal, expense: Decimal, prev_income: Decimal, prev_expense: Decimal) -> Summary:
    cur, prev = period_totals(income, expense), period_totals(prev_income, prev_expense)
    return Summary(
        income=income,
        expense=expense,
        net=cur.net,
        savings_rate=cur.savings_rate,
        prev=prev,
        income_change_pct=change_pct(income, prev_income),
        expense_change_pct=change_pct(expense, prev_expense),
        net_change_pct=change_pct(cur.net, prev.net),
    )


def build_category_changes(
    current: list[CategoryTotal], previous: list[CategoryTotal], *, flag_new: bool = False
) -> list[CategoryChange]:
    """Categorías con movimiento en el mes o en el anterior, ordenadas por total desc (luego nombre).

    Una que bajó a 0 aparece con change_pct = -100; sin mes anterior (prev = 0) change_pct es None
    y, en ingresos (`flag_new`), is_new = True."""
    prev_by_id = {c.category_id: c for c in previous}
    cur_by_id = {c.category_id: c for c in current}
    grand = sum((c.total for c in current), ZERO)
    rows: list[CategoryChange] = []
    for cid in {*cur_by_id, *prev_by_id}:
        cur, prev = cur_by_id.get(cid), prev_by_id.get(cid)
        base = cur or prev
        assert base is not None
        total = cur.total if cur else ZERO
        prev_total = prev.total if prev else ZERO
        rows.append(
            CategoryChange(
                category_id=cid,
                name=base.name,
                color=base.color,
                icon=base.icon,
                total=total,
                prev_total=prev_total,
                change_pct=change_pct(total, prev_total),
                percent=round(float(total / grand * 100), 1) if grand > 0 else 0.0,
                count=cur.count if cur else 0,
                is_new=flag_new and prev_total == 0 and total > 0,
            )
        )
    rows.sort(key=lambda r: (-r.total, r.name.lower()))
    return rows


def build_daily(
    month_start: date, last_day: date, rows: list[DailyTotal]
) -> tuple[list[DailyRow], DailyStats]:
    """Un elemento por día de `month_start` a `last_day` (inclusive) y sus estadísticas."""
    by_date = {r.date: r for r in rows}
    days: list[DailyRow] = []
    d = month_start
    while d <= last_day:
        r = by_date.get(d)
        days.append(
            DailyRow(
                date=d,
                expense=r.expense if r else ZERO,
                income=r.income if r else ZERO,
                is_payday=bool(r and r.paycheck_income > 0),
            )
        )
        d += timedelta(days=1)
    total = sum((x.expense for x in days), ZERO)
    peak = max(days, key=lambda x: (x.expense, -x.date.toordinal()), default=None)
    has_peak = peak is not None and peak.expense > 0
    stats = DailyStats(
        max_day=peak.date if has_peak and peak else None,
        max_day_expense=peak.expense if has_peak and peak else ZERO,
        avg_daily_expense=(total / len(days)).quantize(Decimal("0.01")) if days else ZERO,
        no_spend_days=sum(1 for x in days if x.expense == 0),
    )
    return days, stats


def goal_status(
    *, target_amount: Decimal, saved: Decimal, target_date: date | None,
    monthly_needed: Decimal | None, contributed_this_month: Decimal,
) -> GoalStatus:
    if saved >= target_amount:
        return GoalStatus.COMPLETED
    if target_date is None:
        return GoalStatus.NO_TARGET_DATE
    if monthly_needed is None or contributed_this_month >= monthly_needed:
        return GoalStatus.ON_TRACK
    return GoalStatus.BEHIND


def summarize_budgets(budgets: list[BudgetStatus]) -> BudgetsSummary:
    return BudgetsSummary(
        ok=sum(1 for b in budgets if b.status == BudgetState.OK),
        warning=sum(1 for b in budgets if b.status == BudgetState.WARNING),
        exceeded=sum(1 for b in budgets if b.status == BudgetState.EXCEEDED),
    )
