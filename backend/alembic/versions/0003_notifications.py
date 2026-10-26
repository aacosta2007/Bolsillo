"""Notificaciones: bandeja, suscripciones Web Push y preferencias en users

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLE_OPTS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

# Columnas nuevas de users: NOT NULL con server_default, así las filas existentes quedan con los valores por defecto.
USER_COLUMNS = (
    ("budget_alerts", sa.Boolean(), sa.text("1")),
    ("upcoming_alerts", sa.Boolean(), sa.text("1")),
    ("upcoming_days_before", sa.Integer(), sa.text("1")),
    ("payday_alerts", sa.Boolean(), sa.text("1")),
    ("monthly_report_alerts", sa.Boolean(), sa.text("1")),
    ("notify_hour", sa.Integer(), sa.text("8")),
)


def upgrade() -> None:
    for name, type_, default in USER_COLUMNS:
        op.add_column("users", sa.Column(name, type_, nullable=False, server_default=default))
    op.create_check_constraint("ck_users_upcoming_days_range", "users", "upcoming_days_before BETWEEN 0 AND 7")
    op.create_check_constraint("ck_users_notify_hour_range", "users", "notify_hour BETWEEN 0 AND 23")

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("url", sa.String(255), nullable=False, server_default="/"),
        sa.Column("dedupe_key", sa.String(150), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        # DATETIME(6): varios avisos en el mismo segundo conservan su orden
        sa.Column(
            "created_at",
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql", "mariadb"),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
        **TABLE_OPTS,
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("device", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_push_subscriptions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_push_subscriptions_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
        **TABLE_OPTS,
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])


def downgrade() -> None:
    # Se pierden bandeja, suscripciones y preferencias (no existen en el esquema anterior).
    op.drop_table("push_subscriptions")
    op.drop_table("notifications")
    op.drop_constraint("ck_users_notify_hour_range", "users", type_="check")
    op.drop_constraint("ck_users_upcoming_days_range", "users", type_="check")
    for name, _type, _default in reversed(USER_COLUMNS):
        op.drop_column("users", name)
