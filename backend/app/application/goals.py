from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.application.ports import today_in
from app.domain.entities import Contribution, Goal
from app.domain.exceptions import BusinessRuleError, NotFoundError
from app.domain.repositories import UnitOfWork
from app.domain.rules import goal_percent, monthly_needed


@dataclass(kw_only=True)
class GoalView:
    id: UUID
    name: str
    target_amount: Decimal
    target_date: date | None
    account_id: UUID | None
    color: str
    icon: str
    saved: Decimal
    percent: float
    monthly_needed: Decimal | None
    completed: bool
    created_at: datetime


def to_view(g: Goal, today: date) -> GoalView:
    return GoalView(
        id=g.id, name=g.name, target_amount=g.target_amount, target_date=g.target_date,
        account_id=g.account_id, color=g.color, icon=g.icon, saved=g.saved,
        percent=goal_percent(g.target_amount, g.saved),
        monthly_needed=monthly_needed(g.target_amount, g.saved, g.target_date, today),
        completed=g.saved >= g.target_amount, created_at=g.created_at,
    )


class GoalService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _today(self, user_id: UUID) -> date:
        user = await self.uow.users.get(user_id)
        return today_in(user.timezone if user else "UTC")

    async def _goal(self, user_id: UUID, id: UUID) -> Goal:
        g = await self.uow.goals.get(user_id, id)
        if g is None:
            raise NotFoundError("Meta no encontrada")
        return g

    async def _check_account(self, user_id: UUID, account_id: UUID | None) -> None:
        if account_id is not None and await self.uow.accounts.get(user_id, account_id) is None:
            raise NotFoundError("Cuenta no encontrada")

    async def list(self, user_id: UUID) -> list[GoalView]:
        today = await self._today(user_id)
        return [to_view(g, today) for g in await self.uow.goals.list(user_id)]

    async def get(self, user_id: UUID, id: UUID) -> GoalView:
        return to_view(await self._goal(user_id, id), await self._today(user_id))

    async def create(self, user_id: UUID, data: dict) -> GoalView:
        if data["target_amount"] <= 0:
            raise BusinessRuleError("La meta debe ser mayor que cero")
        await self._check_account(user_id, data.get("account_id"))
        g = Goal(
            user_id=user_id, name=data["name"], target_amount=data["target_amount"],
            target_date=data.get("target_date"), account_id=data.get("account_id"),
            **{k: data[k] for k in ("color", "icon") if data.get(k)},
        )
        await self.uow.goals.add(g)
        await self.uow.commit()
        return await self.get(user_id, g.id)

    async def update(self, user_id: UUID, id: UUID, changes: dict) -> GoalView:
        g = await self._goal(user_id, id)
        for key in ("name", "target_amount", "color", "icon"):
            if changes.get(key) is not None:
                setattr(g, key, changes[key])
        for key in ("target_date", "account_id"):
            if key in changes:
                setattr(g, key, changes[key])
        if g.target_amount <= 0:
            raise BusinessRuleError("La meta debe ser mayor que cero")
        await self._check_account(user_id, g.account_id)
        await self.uow.goals.update(g)
        await self.uow.commit()
        return await self.get(user_id, id)

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self._goal(user_id, id)
        await self.uow.goals.delete(user_id, id)
        await self.uow.commit()

    async def contributions(self, user_id: UUID, goal_id: UUID) -> list[Contribution]:
        await self._goal(user_id, goal_id)
        return await self.uow.goals.list_contributions(user_id, goal_id)

    async def add_contribution(self, user_id: UUID, goal_id: UUID, data: dict) -> Contribution:
        g = await self._goal(user_id, goal_id)
        amount: Decimal = data["amount"]
        if amount == 0:
            raise BusinessRuleError("El aporte no puede ser cero")
        if g.saved + amount < 0:
            raise BusinessRuleError("El ahorro de la meta no puede quedar negativo")
        c = Contribution(
            user_id=user_id, goal_id=goal_id, amount=amount,
            date=data.get("date") or await self._today(user_id), note=data.get("note"),
        )
        await self.uow.goals.add_contribution(c)
        await self.uow.commit()
        return c

    async def delete_contribution(self, user_id: UUID, goal_id: UUID, cid: UUID) -> None:
        g = await self._goal(user_id, goal_id)
        c = await self.uow.goals.get_contribution(user_id, goal_id, cid)
        if c is None:
            raise NotFoundError("Aporte no encontrado")
        if g.saved - c.amount < 0:
            raise BusinessRuleError("Eliminar este aporte dejaría el ahorro de la meta en negativo")
        await self.uow.goals.delete_contribution(user_id, cid)
        await self.uow.commit()
