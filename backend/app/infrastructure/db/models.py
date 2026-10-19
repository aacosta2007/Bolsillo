from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

Money = Numeric(14, 2, asdecimal=True)


class UTCDateTime(TypeDecorator):
    """DATETIME (MariaDB no guarda zona): se almacena en UTC y se devuelve con tzinfo=UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def _id() -> Mapped[UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid4)


def _user_fk() -> Mapped[UUID]:
    return mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


def _created() -> Mapped[datetime]:
    return mapped_column(UTCDateTime(), server_default=func.now(), nullable=False)


def _updated() -> Mapped[datetime]:
    return mapped_column(
        UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = _id()
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Bogota")
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)


class AccountModel(Base):
    __tablename__ = "accounts"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        CheckConstraint("type IN ('cash','bank','credit_card','savings','wallet')", name="type"),
        Index("ix_accounts_user_id", "user_id"),
    )


class CategoryModel(Base):
    __tablename__ = "categories"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        CheckConstraint("kind IN ('income','expense')", name="kind"),
        UniqueConstraint("user_id", "kind", "name", name="uq_categories_user_kind_name"),
    )


class TransactionModel(Base):
    __tablename__ = "transactions"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT")
    )
    transfer_account_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT")
    )
    note: Mapped[str | None] = mapped_column(String(500))
    recurring_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("recurring_rules.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        CheckConstraint("type IN ('income','expense','transfer')", name="type"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "(type = 'transfer' AND transfer_account_id IS NOT NULL AND category_id IS NULL "
            "AND transfer_account_id <> account_id) "
            "OR (type <> 'transfer' AND transfer_account_id IS NULL AND category_id IS NOT NULL)",
            name="shape",
        ),
        Index("ix_transactions_user_date", "user_id", "date"),
        Index("ix_transactions_user_category_date", "user_id", "category_id", "date"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_transfer_account_id", "transfer_account_id"),
        Index("ix_transactions_recurring_id", "recurring_id"),
    )


class BudgetModel(Base):
    __tablename__ = "budgets"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    category_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    amount_limit: Mapped[Decimal] = mapped_column(Money, nullable=False)
    alert_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2, asdecimal=True), nullable=False, default=Decimal("0.80")
    )
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budgets_user_category_month"),
        CheckConstraint("amount_limit > 0", name="limit_positive"),
        CheckConstraint("alert_threshold > 0 AND alert_threshold <= 1", name="threshold_range"),
        Index("ix_budgets_category_id", "category_id"),
    )


class RecurringRuleModel(Base):
    __tablename__ = "recurring_rules"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(500))
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_run_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        CheckConstraint("type IN ('income','expense')", name="type"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("frequency IN ('daily','weekly','monthly','yearly')", name="frequency"),
        CheckConstraint("`interval` >= 1", name="interval_positive"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates"),
        Index("ix_recurring_rules_user_active_next", "user_id", "active", "next_run_date"),
        Index("ix_recurring_rules_account_id", "account_id"),
        Index("ix_recurring_rules_category_id", "category_id"),
    )


class SavingsGoalModel(Base):
    __tablename__ = "savings_goals"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date)
    account_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL")
    )
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="target_positive"),
        Index("ix_savings_goals_user_id", "user_id"),
        Index("ix_savings_goals_account_id", "account_id"),
    )


class GoalContributionModel(Base):
    __tablename__ = "goal_contributions"
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    goal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_nonzero"),
        Index("ix_goal_contributions_goal_date", "goal_id", "date"),
        Index("ix_goal_contributions_user_id", "user_id"),
    )
