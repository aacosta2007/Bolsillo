from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.entities import Budget, BudgetStatus
from app.domain.enums import CategoryKind
from app.domain.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.domain.repositories import UnitOfWork
from app.domain.rules import budget_status, last_of_month


def _check_values(amount_limit: Decimal | None, threshold: Decimal | None) -> None:
    if amount_limit is not None and amount_limit <= 0:
        raise BusinessRuleError("El límite del presupuesto debe ser mayor que cero")
    if threshold is not None and not (Decimal("0") < threshold <= Decimal("1")):
        raise BusinessRuleError("El umbral de alerta debe estar entre 0 y 1")


def to_status(b: Budget, spent: Decimal) -> BudgetStatus:
    remaining, percent, state = budget_status(b.amount_limit, spent, b.alert_threshold)
    return BudgetStatus(
        id=b.id,
        category_id=b.category_id,
        month=b.month,
        amount_limit=b.amount_limit,
        alert_threshold=b.alert_threshold,
        spent=spent,
        remaining=remaining,
        percent=percent,
        status=state,
    )


class BudgetService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _statuses(self, user_id: UUID, budgets: list[Budget], month: date) -> list[BudgetStatus]:
        spent = await self.uow.transactions.spent_by_category(user_id, month, last_of_month(month))
        return [to_status(b, spent.get(b.category_id, Decimal("0.00"))) for b in budgets]

    async def list(self, user_id: UUID, month: date) -> list[BudgetStatus]:
        return await self._statuses(user_id, await self.uow.budgets.list_for_month(user_id, month), month)

    async def _status_of(self, user_id: UUID, b: Budget) -> BudgetStatus:
        return (await self._statuses(user_id, [b], b.month))[0]

    async def get(self, user_id: UUID, id: UUID) -> Budget:
        b = await self.uow.budgets.get(user_id, id)
        if b is None:
            raise NotFoundError("Presupuesto no encontrado")
        return b

    async def create(self, user_id: UUID, data: dict) -> BudgetStatus:
        _check_values(data["amount_limit"], data.get("alert_threshold"))
        cat = await self.uow.categories.get(user_id, data["category_id"])
        if cat is None:
            raise NotFoundError("Categoría no encontrada")
        if cat.kind != CategoryKind.EXPENSE:
            raise BusinessRuleError("Solo se pueden presupuestar categorías de gasto")
        month = data["month"]
        if await self.uow.budgets.find(user_id, cat.id, month):
            raise ConflictError("Ya existe un presupuesto para esa categoría y mes")
        b = Budget(
            user_id=user_id,
            category_id=cat.id,
            month=month,
            amount_limit=data["amount_limit"],
            alert_threshold=data.get("alert_threshold") or Decimal("0.80"),
        )
        await self.uow.budgets.add(b)
        await self.uow.commit()
        return await self._status_of(user_id, b)

    async def update(self, user_id: UUID, id: UUID, changes: dict) -> BudgetStatus:
        b = await self.get(user_id, id)
        _check_values(changes.get("amount_limit"), changes.get("alert_threshold"))
        if changes.get("amount_limit") is not None:
            b.amount_limit = changes["amount_limit"]
        if changes.get("alert_threshold") is not None:
            b.alert_threshold = changes["alert_threshold"]
        await self.uow.budgets.update(b)
        await self.uow.commit()
        return await self._status_of(user_id, b)

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self.get(user_id, id)
        await self.uow.budgets.delete(user_id, id)
        await self.uow.commit()

    async def copy(self, user_id: UUID, from_month: date, to_month: date) -> list[BudgetStatus]:
        """Copia los presupuestos de un mes a otro, omitiendo los que ya existen.
        Devuelve los presupuestos creados."""
        if from_month == to_month:
            raise BusinessRuleError("El mes de origen y destino deben ser distintos")
        created: list[Budget] = []
        for src in await self.uow.budgets.list_for_month(user_id, from_month):
            if await self.uow.budgets.find(user_id, src.category_id, to_month):
                continue
            nb = Budget(
                user_id=user_id,
                category_id=src.category_id,
                month=to_month,
                amount_limit=src.amount_limit,
                alert_threshold=src.alert_threshold,
            )
            await self.uow.budgets.add(nb)
            created.append(nb)
        await self.uow.commit()
        return await self._statuses(user_id, created, to_month)
