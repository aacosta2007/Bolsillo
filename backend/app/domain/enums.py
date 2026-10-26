from enum import StrEnum


class AccountType(StrEnum):
    CASH = "cash"
    BANK = "bank"
    CREDIT_CARD = "credit_card"
    SAVINGS = "savings"
    WALLET = "wallet"


class CategoryKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Frequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    MONTHLY_DAYS = "monthly_days"  # días fijos del mes (quincenal: "15,L")


class WeekendAdjust(StrEnum):
    NONE = "none"
    PREVIOUS_BUSINESS_DAY = "previous_business_day"


class BudgetState(StrEnum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


class NotificationKind(StrEnum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    UPCOMING_RECURRING = "upcoming_recurring"
    PAYDAY = "payday"
    MONTHLY_REPORT = "monthly_report"
    TEST = "test"
