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


class BudgetState(StrEnum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"
