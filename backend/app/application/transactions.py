from __future__ import annotations

from uuid import UUID

from app.domain.entities import Account, Transaction, TransactionFilters
from app.domain.exceptions import NotFoundError
from app.domain.repositories import UnitOfWork
from app.domain.rules import validate_transaction

EDITABLE = ("type", "amount", "date", "account_id", "category_id", "transfer_account_id", "note")


class TransactionService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list(
        self, user_id: UUID, filters: TransactionFilters, page: int, page_size: int
    ) -> tuple[list[Transaction], int]:
        return await self.uow.transactions.list(user_id, filters, page, page_size)

    async def get(self, user_id: UUID, id: UUID) -> Transaction:
        tx = await self.uow.transactions.get(user_id, id)
        if tx is None:
            raise NotFoundError("Movimiento no encontrado")
        return tx

    async def _account(self, user_id: UUID, id: UUID) -> Account:
        acc = await self.uow.accounts.get(user_id, id)
        if acc is None:
            raise NotFoundError("Cuenta no encontrada")
        return acc

    async def _validate(self, tx: Transaction, previous: Transaction | None) -> None:
        user_id = tx.user_id
        account = await self._account(user_id, tx.account_id)
        to_check = []
        if previous is None or previous.account_id != tx.account_id:
            to_check.append(account)
        if tx.transfer_account_id is not None:
            dest = await self._account(user_id, tx.transfer_account_id)
            if previous is None or previous.transfer_account_id != tx.transfer_account_id:
                to_check.append(dest)
        category = None
        if tx.category_id is not None:
            category = await self.uow.categories.get(user_id, tx.category_id)
            if category is None:
                raise NotFoundError("Categoría no encontrada")
        validate_transaction(
            type=tx.type,
            amount=tx.amount,
            account_id=tx.account_id,
            category_id=tx.category_id,
            transfer_account_id=tx.transfer_account_id,
            category=category,
            check_archived=to_check,
        )

    async def create(self, user_id: UUID, data: dict) -> Transaction:
        tx = Transaction(
            user_id=user_id,
            type=data["type"],
            amount=data["amount"],
            date=data["date"],
            account_id=data["account_id"],
            category_id=data.get("category_id"),
            transfer_account_id=data.get("transfer_account_id"),
            note=data.get("note"),
        )
        await self._validate(tx, None)
        await self.uow.transactions.add(tx)
        await self.uow.commit()
        return tx

    async def update(self, user_id: UUID, id: UUID, changes: dict) -> Transaction:
        previous = await self.get(user_id, id)
        tx = Transaction(**{**previous.__dict__})
        for key in EDITABLE:
            if key in changes:
                setattr(tx, key, changes[key])
        tx.__post_init__()
        await self._validate(tx, previous)
        await self.uow.transactions.update(tx)
        await self.uow.commit()
        return tx

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self.get(user_id, id)
        await self.uow.transactions.delete(user_id, id)
        await self.uow.commit()
