from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Callable
from uuid import UUID

from app.application.ports import today_in
from app.domain.entities import RecurringRule, Transaction, UpcomingItem, utcnow
from app.domain.enums import CategoryKind, Frequency, TransactionType, WeekendAdjust
from app.domain.exceptions import BusinessRuleError, NotFoundError
from app.domain.repositories import UnitOfWork
from app.domain.rules import (
    effective_date,
    first_nominal_on_or_after,
    next_nominal_after,
    normalize_days_of_month,
)

log = logging.getLogger(__name__)

MAX_PER_RULE = 1000  # tope de seguridad por regla y ejecución
EDITABLE = (
    "type", "amount", "account_id", "category_id", "note", "frequency", "interval",
    "start_date", "end_date", "active", "days_of_month", "weekend_adjust", "is_paycheck",
)
SCHEDULE_FIELDS = ("start_date", "frequency", "interval", "days_of_month", "weekend_adjust")
NULLABLE_FIELDS = ("end_date", "note", "days_of_month")
MAX_WEEKEND_SHIFT = 2  # el ajuste de fin de semana adelanta la fecha como máximo 2 días


class RecurringService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list(self, user_id: UUID) -> list[RecurringRule]:
        return await self.uow.recurring.list(user_id)

    async def get(self, user_id: UUID, id: UUID) -> RecurringRule:
        r = await self.uow.recurring.get(user_id, id)
        if r is None:
            raise NotFoundError("Regla recurrente no encontrada")
        return r

    async def _validate(self, rule: RecurringRule, check_account: bool) -> None:
        if rule.type == TransactionType.TRANSFER:
            raise BusinessRuleError("Los recurrentes solo pueden ser ingresos o gastos")
        if rule.amount <= 0:
            raise BusinessRuleError("El monto debe ser mayor que cero")
        if rule.interval < 1:
            raise BusinessRuleError("El intervalo debe ser al menos 1")
        if rule.frequency == Frequency.MONTHLY_DAYS:
            rule.days_of_month = normalize_days_of_month(rule.days_of_month)
            rule.interval = 1  # con días fijos el intervalo no aplica
        elif rule.days_of_month is not None:
            raise BusinessRuleError("days_of_month solo se admite con la frecuencia monthly_days")
        if rule.is_paycheck and rule.type != TransactionType.INCOME:
            raise BusinessRuleError("Solo un ingreso puede marcarse como sueldo (is_paycheck)")
        if rule.end_date is not None and rule.end_date < rule.start_date:
            raise BusinessRuleError("La fecha de fin no puede ser anterior a la de inicio")
        acc = await self.uow.accounts.get(rule.user_id, rule.account_id)
        if acc is None:
            raise NotFoundError("Cuenta no encontrada")
        if check_account and acc.archived:
            raise BusinessRuleError("La cuenta está archivada")
        cat = await self.uow.categories.get(rule.user_id, rule.category_id)
        if cat is None:
            raise NotFoundError("Categoría no encontrada")
        if cat.kind != CategoryKind(rule.type.value):
            raise BusinessRuleError("El tipo de la categoría no coincide con el tipo de la regla")

    @staticmethod
    def _advance(rule: RecurringRule) -> date:
        """Siguiente ocurrencia nominal de la regla tras `next_run_date`."""
        return next_nominal_after(
            rule.start_date, rule.frequency, rule.interval, rule.days_of_month, rule.next_run_date
        )

    async def create(self, user_id: UUID, data: dict) -> RecurringRule:
        rule = RecurringRule(
            user_id=user_id,
            type=data["type"],
            amount=data["amount"],
            account_id=data["account_id"],
            category_id=data["category_id"],
            note=data.get("note"),
            frequency=data["frequency"],
            interval=data.get("interval") or 1,
            days_of_month=data.get("days_of_month"),
            weekend_adjust=data.get("weekend_adjust") or WeekendAdjust.NONE,
            is_paycheck=data.get("is_paycheck", False),
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            next_run_date=data["start_date"],
            active=data.get("active", True),
        )
        await self._validate(rule, check_account=True)
        rule.next_run_date = first_nominal_on_or_after(
            rule.start_date, rule.frequency, rule.interval, rule.days_of_month, rule.start_date
        )
        await self.uow.recurring.add(rule)
        await self.uow.commit()
        return rule

    async def update(self, user_id: UUID, id: UUID, changes: dict, today: date | None = None) -> RecurringRule:
        rule = await self.get(user_id, id)
        schedule_changed = False
        if changes.get("frequency") not in (None, Frequency.MONTHLY_DAYS) and "days_of_month" not in changes:
            changes = {**changes, "days_of_month": None}  # al salir de monthly_days se limpian los días
        for key in EDITABLE:
            if key in changes and (changes[key] is not None or key in NULLABLE_FIELDS):
                if key in SCHEDULE_FIELDS and changes[key] != getattr(rule, key):
                    schedule_changed = True
                setattr(rule, key, changes[key])
        rule.__post_init__()
        await self._validate(rule, check_account="account_id" in changes)
        if schedule_changed:
            # Nunca regenera el pasado: la próxima ejecución es la primera ocurrencia desde hoy.
            today = today or today_in((await self.uow.users.get(user_id)).timezone)
            rule.next_run_date = first_nominal_on_or_after(
                rule.start_date, rule.frequency, rule.interval, rule.days_of_month, today
            )
            if rule.start_date < today:
                # con ajuste de fin de semana, una ocurrencia nominal próxima puede tener ya vencida su fecha efectiva
                while effective_date(rule.next_run_date, rule.weekend_adjust) < today:
                    rule.next_run_date = self._advance(rule)
        await self.uow.recurring.update(rule)
        await self.uow.commit()
        return rule

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self.get(user_id, id)
        await self.uow.recurring.delete(user_id, id)
        await self.uow.commit()

    async def run(self, user_id: UUID, today: date) -> int:
        """Genera los movimientos pendientes hasta `today`. Idempotente: las reglas se
        bloquean (FOR UPDATE) y next_run_date avanza en la misma transacción.
        next_run_date es la fecha nominal; el movimiento y end_date usan la fecha efectiva."""
        created = 0
        for rule in await self.uow.recurring.lock_due(user_id, today):
            n = 0
            while n < MAX_PER_RULE:
                due = effective_date(rule.next_run_date, rule.weekend_adjust)
                if due > today or (rule.end_date is not None and due > rule.end_date):
                    break
                await self.uow.transactions.add(
                    Transaction(
                        user_id=user_id,
                        type=rule.type,
                        amount=rule.amount,
                        date=due,
                        account_id=rule.account_id,
                        category_id=rule.category_id,
                        note=rule.note,
                        recurring_id=rule.id,
                    )
                )
                rule.next_run_date = self._advance(rule)
                n += 1
            if rule.end_date is not None and effective_date(rule.next_run_date, rule.weekend_adjust) > rule.end_date:
                rule.active = False
            rule.updated_at = utcnow()
            await self.uow.recurring.update(rule)
            created += n
        await self.uow.commit()
        return created

    async def upcoming(self, user_id: UUID, days: int, today: date) -> list[UpcomingItem]:
        horizon = today + timedelta(days=days)
        items: list[UpcomingItem] = []
        for rule in await self.uow.recurring.list(user_id):
            if not rule.active:
                continue
            nominal, n = rule.next_run_date, 0
            # la fecha efectiva es <= nominal (hasta 2 días antes): se recorre con holgura y se filtra
            while nominal <= horizon + timedelta(days=MAX_WEEKEND_SHIFT) and n < 500:
                d = effective_date(nominal, rule.weekend_adjust)
                if rule.end_date is not None and d > rule.end_date:
                    break
                if today <= d <= horizon:
                    items.append(
                        UpcomingItem(
                            rule_id=rule.id, date=d, type=rule.type, amount=rule.amount,
                            category_id=rule.category_id, account_id=rule.account_id, note=rule.note,
                            is_paycheck=rule.is_paycheck,
                        )
                    )
                nominal = next_nominal_after(
                    rule.start_date, rule.frequency, rule.interval, rule.days_of_month, nominal
                )
                n += 1
        items.sort(key=lambda i: (i.date, str(i.rule_id)))
        return items


async def run_pending_for_all_users(uow_factory: Callable[[], UnitOfWork]) -> int:
    """Ejecuta los recurrentes pendientes de todos los usuarios (job diario y arranque)."""
    async with uow_factory() as uow:
        users = await uow.users.list_all()
    total = 0
    for user in users:
        try:
            async with uow_factory() as uow:
                total += await RecurringService(uow).run(user.id, today_in(user.timezone))
        except Exception:  # un usuario con error no debe frenar a los demás
            log.exception("Fallo ejecutando recurrentes del usuario %s", user.id)
    if total:
        log.info("Recurrentes: %s movimientos generados", total)
    return total


__all__ = ["RecurringService", "run_pending_for_all_users", "Frequency"]
