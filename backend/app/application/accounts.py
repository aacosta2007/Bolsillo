from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.domain.entities import Account, utcnow
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.repositories import UnitOfWork

EDITABLE = ("name", "type", "initial_balance", "color", "icon", "archived")


class AccountService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list(self, user_id: UUID, include_archived: bool = False) -> list[Account]:
        return await self.uow.accounts.list(user_id, include_archived)

    async def get(self, user_id: UUID, id: UUID) -> Account:
        acc = await self.uow.accounts.get(user_id, id)
        if acc is None:
            raise NotFoundError("Cuenta no encontrada")
        return acc

    async def create(self, user_id: UUID, data: dict) -> Account:
        acc = Account(
            user_id=user_id,
            name=data["name"],
            type=data["type"],
            initial_balance=data.get("initial_balance") or Decimal("0.00"),
            **{k: data[k] for k in ("color", "icon") if data.get(k)},
        )
        await self.uow.accounts.add(acc)
        await self.uow.commit()
        return await self.get(user_id, acc.id)

    async def update(self, user_id: UUID, id: UUID, changes: dict) -> Account:
        acc = await self.get(user_id, id)
        for key in EDITABLE:
            if key in changes and changes[key] is not None:
                setattr(acc, key, changes[key])
        acc.__post_init__()
        acc.updated_at = utcnow()
        await self.uow.accounts.update(acc)
        await self.uow.commit()
        return await self.get(user_id, id)

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self.get(user_id, id)
        if await self.uow.accounts.has_dependencies(user_id, id):
            raise ConflictError(
                "La cuenta tiene movimientos o reglas recurrentes; archívala en lugar de eliminarla"
            )
        await self.uow.accounts.delete(user_id, id)
        await self.uow.commit()
