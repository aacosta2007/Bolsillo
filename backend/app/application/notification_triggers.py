"""Disparadores de avisos: presupuestos, recurrentes próximos, sueldo y reporte mensual.

Ningún método propaga excepciones: un aviso fallido nunca debe romper la operación del usuario."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable
from uuid import UUID

from app.application.budgets import to_status
from app.application.notifications import NotificationService
from app.application.ports import PushSender, today_in
from app.application.recurring import GeneratedPaycheck, RecurringService
from app.application.reports import ReportService
from app.domain import notification_texts as texts
from app.domain.entities import Budget, Transaction, TransactionFilters, User
from app.domain.enums import BudgetState, NotificationKind, TransactionType
from app.domain.notification_schedule import users_due
from app.domain.repositories import UnitOfWork
from app.domain.rules import add_months, first_of_month, last_of_month

log = logging.getLogger(__name__)

PAYDAY_MAX_AGE_DAYS = 3  # no se avisa de sueldos antiguos regenerados por una recuperación


class NotificationTriggers:
    def __init__(self, uow: UnitOfWork, notifier: NotificationService):
        self.uow = uow
        self.notifier = notifier

    # ---- presupuestos ----
    async def _check_budget(self, user: User, budget: Budget, today: date) -> None:
        month_end = last_of_month(budget.month)
        spent = (await self.uow.transactions.spent_by_category(user.id, budget.month, month_end)).get(
            budget.category_id, Decimal("0.00")
        )
        st = to_status(budget, spent)
        if st.status == BudgetState.OK:
            return
        cat = await self.uow.categories.get(user.id, budget.category_id)
        name = cat.name if cat else "Presupuesto"
        month = budget.month.strftime("%Y-%m")
        if st.status == BudgetState.EXCEEDED:
            await self.notifier.notify_message(
                user.id, NotificationKind.BUDGET_EXCEEDED, f"budget:{budget.id}:{month}:exceeded",
                texts.budget_exceeded(name, st.spent, st.amount_limit),
            )
        else:
            days_left = (month_end - today).days + 1 if budget.month == first_of_month(today) else None
            await self.notifier.notify_message(
                user.id, NotificationKind.BUDGET_WARNING, f"budget:{budget.id}:{month}:warning",
                texts.budget_warning(name, st.percent, st.remaining, days_left),
            )

    async def after_transaction(self, user: User, tx: Transaction) -> None:
        """Tras crear/editar un movimiento: evalúa el presupuesto de su categoría y mes."""
        if tx.type != TransactionType.EXPENSE or tx.category_id is None:
            return
        try:
            budget = await self.uow.budgets.find(user.id, tx.category_id, first_of_month(tx.date))
            if budget is not None:
                await self._check_budget(user, budget, today_in(user.timezone))
        except Exception:
            log.exception("Fallo evaluando presupuesto tras movimiento (usuario %s)", user.id)
            await self._safe_rollback()

    # ---- sueldo ----
    async def paychecks_generated(self, user: User, generated: list[GeneratedPaycheck]) -> None:
        try:
            today = today_in(user.timezone)
            for g in generated:
                if g.date < today - timedelta(days=PAYDAY_MAX_AGE_DAYS):
                    continue
                period = (await ReportService(self.uow).pay_periods(user.id, 1))[0]
                await self.notifier.notify_message(
                    user.id, NotificationKind.PAYDAY, f"payday:{g.rule_id}:{g.date.isoformat()}",
                    texts.payday(g.amount, period.available_per_day, period.end),
                )
        except Exception:
            log.exception("Fallo avisando sueldo (usuario %s)", user.id)
            await self._safe_rollback()

    # ---- diario (a la hora local del usuario) ----
    async def _upcoming(self, user: User, today: date) -> None:
        if not user.upcoming_alerts:
            return
        days = user.upcoming_days_before
        target = today + timedelta(days=days)
        # (rule_id, fecha) -> (nota, monto, category_id, account_id, es_ingreso)
        items: dict[tuple[UUID, date], tuple[str | None, Decimal, UUID | None, UUID, bool]] = {}
        for it in await RecurringService(self.uow).upcoming(user.id, days, today):
            if it.date == target and not it.is_paycheck:
                items[(it.rule_id, it.date)] = (
                    it.note, it.amount, it.category_id, it.account_id, it.type == TransactionType.INCOME
                )
        if days == 0:
            # las ocurrencias de hoy ya las generó el job de las 00:05: se recuperan de los movimientos
            txs, _ = await self.uow.transactions.list(
                user.id, TransactionFilters(date_from=today, date_to=today), 1, 200
            )
            for t in txs:
                if t.recurring_id is None or (t.recurring_id, t.date) in items:
                    continue
                rule = await self.uow.recurring.get(user.id, t.recurring_id)
                if rule is None or rule.is_paycheck:
                    continue
                items[(rule.id, t.date)] = (
                    t.note, t.amount, t.category_id, t.account_id, t.type == TransactionType.INCOME
                )
        for (rule_id, day), (note, amount, category_id, account_id, is_income) in items.items():
            name = note
            if not name:
                cat = await self.uow.categories.get(user.id, category_id) if category_id else None
                name = cat.name if cat else "Recurrente"
            acc = await self.uow.accounts.get(user.id, account_id)
            await self.notifier.notify_message(
                user.id, NotificationKind.UPCOMING_RECURRING, f"upcoming:{rule_id}:{day.isoformat()}",
                texts.upcoming_recurring(name, amount, acc.name if acc else None, is_income, day, days),
            )

    async def _monthly_report(self, user: User, today: date) -> None:
        if today.day != 1 or not user.monthly_report_alerts:
            return
        prev = add_months(today, -1)
        await self.notifier.notify_message(
            user.id, NotificationKind.MONTHLY_REPORT, f"report:{prev.strftime('%Y-%m')}",
            texts.monthly_report(prev),
        )

    async def _budgets_backup(self, user: User, today: date) -> None:
        if not user.budget_alerts:
            return
        for b in await self.uow.budgets.list_for_month(user.id, first_of_month(today)):
            await self._check_budget(user, b, today)

    async def daily(self, user: User, local_now: datetime) -> None:
        today = local_now.date()
        for step in (self._budgets_backup, self._upcoming, self._monthly_report):
            try:
                await step(user, today)
            except Exception:
                log.exception("Fallo en aviso diario %s (usuario %s)", step.__name__, user.id)
                await self._safe_rollback()

    async def _safe_rollback(self) -> None:
        try:
            await self.uow.rollback()
        except Exception:
            pass


async def run_daily_notifications(
    uow_factory: Callable[[], UnitOfWork], sender: PushSender, now_utc: datetime | None = None
) -> int:
    """Job horario: procesa a los usuarios cuya hora local es su `notify_hour`. La dedupe evita
    repetir si el job corre más de una vez en la misma hora. Devuelve cuántos usuarios procesó."""
    now_utc = now_utc or datetime.now(timezone.utc)
    async with uow_factory() as uow:
        users = await uow.users.list_all()
    due = users_due(users, now_utc)
    for user, local in due:
        try:
            async with uow_factory() as uow:
                await NotificationTriggers(uow, NotificationService(uow, sender)).daily(user, local)
        except Exception:
            log.exception("Fallo en avisos diarios del usuario %s", user.id)
    return len(due)
