"""Schemas Pydantic (request/response). El dinero sale como string con 2 decimales."""
from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal
from typing import Annotated, ClassVar, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

from app.domain.enums import (
    AccountType,
    BudgetState,
    CategoryKind,
    Frequency,
    TransactionType,
)


def _fmt(v: Decimal) -> str:
    return f"{v:.2f}"


Date = dt.date

Money = Annotated[Decimal, PlainSerializer(_fmt, return_type=str, when_used="json")]
MoneyIn = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]
ThresholdIn = Annotated[Decimal, Field(max_digits=3, decimal_places=2)]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Icon = Annotated[str, Field(min_length=1, max_length=50)]
Name = Annotated[str, Field(min_length=1, max_length=100)]
Note = Annotated[str, Field(max_length=500)]


def _month_str(v):
    return v.strftime("%Y-%m") if isinstance(v, dt.date) else v


MonthStr = Annotated[str, BeforeValidator(_month_str)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UpdateBase(BaseModel):
    """PATCH parcial: solo se aplican los campos enviados; null solo en campos anulables."""

    NULLABLE: ClassVar[set[str]] = set()

    def changes(self) -> dict:
        return {
            k: v
            for k, v in self.model_dump(exclude_unset=True).items()
            if v is not None or k in self.NULLABLE
        }


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(ORM):
    id: UUID
    email: str
    display_name: str | None
    currency: str
    timezone: str
    created_at: datetime


class UserUpdate(UpdateBase):
    NULLABLE = {"display_name"}
    currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    timezone: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("currency")
    @classmethod
    def _upper(cls, v):
        return v.upper() if v else v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v):
        if v is None:
            return v
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("Zona horaria inválida") from None
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


# ---------- Cuentas ----------
class AccountOut(ORM):
    id: UUID
    name: str
    type: AccountType
    initial_balance: Money
    color: str
    icon: str
    archived: bool
    balance: Money
    created_at: datetime


class AccountCreate(BaseModel):
    name: Name
    type: AccountType
    initial_balance: MoneyIn = Decimal("0")
    color: Color | None = None
    icon: Icon | None = None


class AccountUpdate(UpdateBase):
    name: Name | None = None
    type: AccountType | None = None
    initial_balance: MoneyIn | None = None
    color: Color | None = None
    icon: Icon | None = None
    archived: bool | None = None


# ---------- Categorías ----------
class CategoryOut(ORM):
    id: UUID
    name: str
    kind: CategoryKind
    icon: str
    color: str
    parent_id: UUID | None


class CategoryCreate(BaseModel):
    name: Name
    kind: CategoryKind
    icon: Icon | None = None
    color: Color | None = None
    parent_id: UUID | None = None


class CategoryUpdate(UpdateBase):
    NULLABLE = {"parent_id"}
    name: Name | None = None
    kind: CategoryKind | None = None
    icon: Icon | None = None
    color: Color | None = None
    parent_id: UUID | None = None


# ---------- Movimientos ----------
class TransactionOut(ORM):
    id: UUID
    type: TransactionType
    amount: Money
    date: Date
    account_id: UUID
    category_id: UUID | None
    transfer_account_id: UUID | None
    note: str | None
    recurring_id: UUID | None
    created_at: datetime


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: MoneyIn
    date: Date
    account_id: UUID
    category_id: UUID | None = None
    transfer_account_id: UUID | None = None
    note: Note | None = None


class TransactionUpdate(UpdateBase):
    NULLABLE = {"category_id", "transfer_account_id", "note"}
    type: TransactionType | None = None
    amount: MoneyIn | None = None
    date: Date | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    transfer_account_id: UUID | None = None
    note: Note | None = None


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------- Presupuestos ----------
class BudgetStatusOut(ORM):
    id: UUID
    category_id: UUID
    month: MonthStr
    amount_limit: Money
    alert_threshold: Money
    spent: Money
    remaining: Money
    percent: float
    status: BudgetState


class BudgetCreate(BaseModel):
    category_id: UUID
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount_limit: MoneyIn
    alert_threshold: ThresholdIn | None = None


class BudgetUpdate(UpdateBase):
    amount_limit: MoneyIn | None = None
    alert_threshold: ThresholdIn | None = None


class BudgetCopy(BaseModel):
    from_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    to_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------- Recurrentes ----------
class RecurringOut(ORM):
    id: UUID
    type: TransactionType
    amount: Money
    account_id: UUID
    category_id: UUID
    note: str | None
    frequency: Frequency
    interval: int
    start_date: Date
    end_date: Date | None
    next_run_date: Date
    active: bool


class RecurringCreate(BaseModel):
    type: TransactionType
    amount: MoneyIn
    account_id: UUID
    category_id: UUID
    note: Note | None = None
    frequency: Frequency
    interval: int = Field(default=1, ge=1, le=365)
    start_date: Date
    end_date: Date | None = None
    active: bool = True


class RecurringUpdate(UpdateBase):
    NULLABLE = {"end_date", "note"}
    type: TransactionType | None = None
    amount: MoneyIn | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    note: Note | None = None
    frequency: Frequency | None = None
    interval: int | None = Field(default=None, ge=1, le=365)
    start_date: Date | None = None
    end_date: Date | None = None
    active: bool | None = None


class RunResult(BaseModel):
    created: int


class UpcomingOut(ORM):
    rule_id: UUID
    date: Date
    type: TransactionType
    amount: Money
    category_id: UUID
    account_id: UUID
    note: str | None


# ---------- Metas ----------
class GoalOut(ORM):
    id: UUID
    name: str
    target_amount: Money
    target_date: Date | None
    account_id: UUID | None
    color: str
    icon: str
    saved: Money
    percent: float
    monthly_needed: Money | None
    completed: bool
    created_at: datetime


class GoalCreate(BaseModel):
    name: Name
    target_amount: MoneyIn
    target_date: Date | None = None
    account_id: UUID | None = None
    color: Color | None = None
    icon: Icon | None = None


class GoalUpdate(UpdateBase):
    NULLABLE = {"target_date", "account_id"}
    name: Name | None = None
    target_amount: MoneyIn | None = None
    target_date: Date | None = None
    account_id: UUID | None = None
    color: Color | None = None
    icon: Icon | None = None


class ContributionOut(ORM):
    id: UUID
    goal_id: UUID
    amount: Money
    date: Date
    note: str | None


class ContributionCreate(BaseModel):
    amount: MoneyIn
    date: Date | None = None
    note: Note | None = None


# ---------- Dashboard / reportes ----------
class CategoryReportOut(ORM):
    category_id: UUID
    name: str
    color: str
    icon: str
    total: Money
    percent: float


class CategoryReportCountOut(CategoryReportOut):
    count: int


class TrendOut(ORM):
    month: str
    income: Money
    expense: Money


class TrendNetOut(TrendOut):
    net: Money


class DashboardOut(BaseModel):
    period: dict[str, Date]
    total_balance: Money
    income: Money
    expense: Money
    net: Money
    savings_rate: float
    by_category: list[CategoryReportOut]
    monthly_trend: list[TrendOut]
    accounts: list[AccountOut]
    budgets_at_risk: list[BudgetStatusOut]
    upcoming_recurring: list[UpcomingOut]
    recent_transactions: list[TransactionOut]
