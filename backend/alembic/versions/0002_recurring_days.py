"""Recurrentes por días del mes (monthly_days), ajuste de fin de semana y sueldo

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

T = "recurring_rules"


def upgrade() -> None:
    # frequency pasa de VARCHAR(10) a VARCHAR(20): 'monthly_days' mide 12.
    # MariaDB no deja alterar una columna usada en un CHECK: se suelta primero y se recrea.
    op.drop_constraint("ck_recurring_rules_frequency", T, type_="check")
    op.alter_column(T, "frequency", existing_type=sa.String(10), type_=sa.String(20), existing_nullable=False)
    op.add_column(T, sa.Column("days_of_month", sa.String(20), nullable=True))
    # NOT NULL con server_default: las filas existentes quedan con 'none' / 0.
    op.add_column(T, sa.Column("weekend_adjust", sa.String(30), nullable=False, server_default="none"))
    op.add_column(T, sa.Column("is_paycheck", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.create_check_constraint(
        "ck_recurring_rules_frequency", T,
        "frequency IN ('daily','weekly','monthly','yearly','monthly_days')",
    )
    op.create_check_constraint(
        "ck_recurring_rules_weekend_adjust", T, "weekend_adjust IN ('none','previous_business_day')"
    )


def downgrade() -> None:
    # Las reglas monthly_days no tienen equivalente en el esquema anterior: se eliminan
    # (los movimientos ya generados se conservan; recurring_id queda en NULL por ON DELETE SET NULL).
    op.execute(f"DELETE FROM {T} WHERE frequency = 'monthly_days'")
    op.drop_constraint("ck_recurring_rules_weekend_adjust", T, type_="check")
    op.drop_constraint("ck_recurring_rules_frequency", T, type_="check")
    op.drop_column(T, "is_paycheck")
    op.drop_column(T, "weekend_adjust")
    op.drop_column(T, "days_of_month")
    op.alter_column(T, "frequency", existing_type=sa.String(20), type_=sa.String(10), existing_nullable=False)
    op.create_check_constraint(
        "ck_recurring_rules_frequency", T, "frequency IN ('daily','weekly','monthly','yearly')"
    )
