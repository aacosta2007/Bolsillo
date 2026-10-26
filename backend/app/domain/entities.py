from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.enums import (
    AccountType,
    BudgetState,
    CategoryKind,
    Frequency,
    TransactionType,
    WeekendAdjust,
)

ZERO = Decimal("0.00")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True)
class User:
    email: str
    password_hash: str
    display_name: str | None = None
    currency: str = "COP"
    timezone: str = "America/Bogota"
    # Preferencias de notificaciones
    budget_alerts: bool = True
    upcoming_alerts: bool = True
    upcoming_days_before: int = 1  # 0-7 (0 = el mismo día)
    payday_alerts: bool = True
    monthly_report_alerts: bool = True
    notify_hour: int = 8  # 0-23, hora local del usuario
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class RefreshToken:
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class Account:
    user_id: UUID
    name: str
    type: AccountType
    initial_balance: Decimal = ZERO
    color: str = "#2563eb"
    icon: str = "wallet"
    archived: bool = False
    balance: Decimal = ZERO  # calculado (no persistido)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.type = AccountType(self.type)


@dataclass(kw_only=True)
class Category:
    user_id: UUID
    name: str
    kind: CategoryKind
    icon: str = "circle"
    color: str = "#64748b"
    parent_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.kind = CategoryKind(self.kind)


@dataclass(kw_only=True)
class Transaction:
    user_id: UUID
    type: TransactionType
    amount: Decimal
    date: date
    account_id: UUID
    category_id: UUID | None = None
    transfer_account_id: UUID | None = None
    note: str | None = None
    recurring_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.type = TransactionType(self.type)


@dataclass(kw_only=True)
class Budget:
    user_id: UUID
    category_id: UUID
    month: date  # siempre el día 1
    amount_limit: Decimal
    alert_threshold: Decimal = Decimal("0.80")
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class BudgetStatus:
    id: UUID
    category_id: UUID
    month: date
    amount_limit: Decimal
    alert_threshold: Decimal
    spent: Decimal
    remaining: Decimal
    percent: float
    status: BudgetState


@dataclass(kw_only=True)
class RecurringRule:
    user_id: UUID
    type: TransactionType
    amount: Decimal
    account_id: UUID
    category_id: UUID
    frequency: Frequency
    start_date: date
    next_run_date: date
    note: str | None = None
    interval: int = 1
    end_date: date | None = None
    days_of_month: str | None = None  # solo monthly_days; normalizado, p. ej. "15,L"
    weekend_adjust: WeekendAdjust = WeekendAdjust.NONE
    is_paycheck: bool = False
    active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.type = TransactionType(self.type)
        self.frequency = Frequency(self.frequency)
        self.weekend_adjust = WeekendAdjust(self.weekend_adjust)


@dataclass(kw_only=True)
class UpcomingItem:
    rule_id: UUID
    date: date
    type: TransactionType
    amount: Decimal
    category_id: UUID
    account_id: UUID
    note: str | None
    is_paycheck: bool = False


@dataclass(kw_only=True)
class Goal:
    user_id: UUID
    name: str
    target_amount: Decimal
    target_date: date | None = None
    account_id: UUID | None = None
    color: str = "#10b981"
    icon: str = "piggy-bank"
    saved: Decimal = ZERO  # calculado (no persistido)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class Contribution:
    user_id: UUID
    goal_id: UUID
    amount: Decimal
    date: date
    note: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class Notification:
    user_id: UUID
    kind: str
    title: str
    body: str
    dedupe_key: str
    url: str = "/"
    read: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class PushSubscription:
    user_id: UUID
    endpoint: str
    p256dh: str
    auth: str
    device: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


# ---- Modelos de lectura (agregaciones) ----
@dataclass(kw_only=True)
class CategoryTotal:
    category_id: UUID
    name: str
    color: str
    icon: str
    total: Decimal
    count: int


@dataclass(kw_only=True)
class MonthlyTotal:
    month: date  # primer día del mes
    income: Decimal
    expense: Decimal


@dataclass(kw_only=True)
class ExportRow:
    date: date
    type: TransactionType
    amount: Decimal
    account: str
    category: str | None
    transfer_account: str | None
    note: str | None


@dataclass(kw_only=True)
class TransactionFilters:
    date_from: date | None = None
    date_to: date | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    type: TransactionType | None = None
    q: str | None = None


@dataclass(kw_only=True)
class DailyTotal:
    date: date
    income: Decimal
    expense: Decimal
    paycheck_income: Decimal  # ingresos de reglas marcadas is_paycheck ese día


@dataclass(kw_only=True)
class TopExpense:
    transaction_id: UUID
    date: date
    note: str | None
    category: str | None
    account: str
    amount: Decimal


@dataclass(kw_only=True)
class ContributionTotals:
    """Aportes de una meta: dentro de un rango y posteriores a su fin (para reconstruir el ahorro a fin de mes)."""
    in_range: Decimal
    after: Decimal
