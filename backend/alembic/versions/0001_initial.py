"""Esquema inicial de Bolsillo (MariaDB 11.4, InnoDB, utf8mb4)

Revision ID: 0001
Revises:
Create Date: 2026-10-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

MONEY = sa.Numeric(14, 2)
TABLE_OPTS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        **TABLE_OPTS,
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_refresh_tokens_user_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        **TABLE_OPTS,
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("initial_balance", MONEY, nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_accounts_user_id_users", ondelete="CASCADE"),
        sa.CheckConstraint("type IN ('cash','bank','credit_card','savings','wallet')", name="ck_accounts_type"),
        **TABLE_OPTS,
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("parent_id", sa.Uuid()),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_categories_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], name="fk_categories_parent_id_categories", ondelete="SET NULL"),
        sa.CheckConstraint("kind IN ('income','expense')", name="ck_categories_kind"),
        sa.UniqueConstraint("user_id", "kind", "name", name="uq_categories_user_kind_name"),
        **TABLE_OPTS,
    )

    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("frequency", sa.String(10), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_rules"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_recurring_rules_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_recurring_rules_account_id_accounts", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_recurring_rules_category_id_categories", ondelete="RESTRICT"),
        sa.CheckConstraint("type IN ('income','expense')", name="ck_recurring_rules_type"),
        sa.CheckConstraint("amount > 0", name="ck_recurring_rules_amount_positive"),
        sa.CheckConstraint("frequency IN ('daily','weekly','monthly','yearly')", name="ck_recurring_rules_frequency"),
        sa.CheckConstraint("`interval` >= 1", name="ck_recurring_rules_interval_positive"),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_recurring_rules_dates"),
        **TABLE_OPTS,
    )
    op.create_index("ix_recurring_rules_user_active_next", "recurring_rules", ["user_id", "active", "next_run_date"])
    op.create_index("ix_recurring_rules_account_id", "recurring_rules", ["account_id"])
    op.create_index("ix_recurring_rules_category_id", "recurring_rules", ["category_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid()),
        sa.Column("transfer_account_id", sa.Uuid()),
        sa.Column("note", sa.String(500)),
        sa.Column("recurring_id", sa.Uuid()),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_transactions_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_transactions_account_id_accounts", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_transactions_category_id_categories", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transfer_account_id"], ["accounts.id"], name="fk_transactions_transfer_account_id_accounts", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recurring_id"], ["recurring_rules.id"], name="fk_transactions_recurring_id_recurring_rules", ondelete="SET NULL"),
        sa.CheckConstraint("type IN ('income','expense','transfer')", name="ck_transactions_type"),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(
            "(type = 'transfer' AND transfer_account_id IS NOT NULL AND category_id IS NULL "
            "AND transfer_account_id <> account_id) "
            "OR (type <> 'transfer' AND transfer_account_id IS NULL AND category_id IS NOT NULL)",
            name="ck_transactions_shape",
        ),
        **TABLE_OPTS,
    )
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "date"])
    op.create_index("ix_transactions_user_category_date", "transactions", ["user_id", "category_id", "date"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_transfer_account_id", "transactions", ["transfer_account_id"])
    op.create_index("ix_transactions_recurring_id", "transactions", ["recurring_id"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("amount_limit", MONEY, nullable=False),
        sa.Column("alert_threshold", sa.Numeric(3, 2), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_budgets_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_budgets_category_id_categories", ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "category_id", "month", name="uq_budgets_user_category_month"),
        sa.CheckConstraint("amount_limit > 0", name="ck_budgets_limit_positive"),
        sa.CheckConstraint("alert_threshold > 0 AND alert_threshold <= 1", name="ck_budgets_threshold_range"),
        **TABLE_OPTS,
    )
    op.create_index("ix_budgets_category_id", "budgets", ["category_id"])

    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("target_amount", MONEY, nullable=False),
        sa.Column("target_date", sa.Date()),
        sa.Column("account_id", sa.Uuid()),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_savings_goals"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_savings_goals_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_savings_goals_account_id_accounts", ondelete="SET NULL"),
        sa.CheckConstraint("target_amount > 0", name="ck_savings_goals_target_positive"),
        **TABLE_OPTS,
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])
    op.create_index("ix_savings_goals_account_id", "savings_goals", ["account_id"])

    op.create_table(
        "goal_contributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(500)),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_goal_contributions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_goal_contributions_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["savings_goals.id"], name="fk_goal_contributions_goal_id_savings_goals", ondelete="CASCADE"),
        sa.CheckConstraint("amount <> 0", name="ck_goal_contributions_amount_nonzero"),
        **TABLE_OPTS,
    )
    op.create_index("ix_goal_contributions_goal_date", "goal_contributions", ["goal_id", "date"])
    op.create_index("ix_goal_contributions_user_id", "goal_contributions", ["user_id"])


def downgrade() -> None:
    for table in (
        "goal_contributions", "savings_goals", "budgets", "transactions", "recurring_rules",
        "categories", "accounts", "refresh_tokens", "users",
    ):
        op.drop_table(table)
