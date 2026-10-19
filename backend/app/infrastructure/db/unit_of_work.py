from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.sql import (
    SqlAccountRepository,
    SqlBudgetRepository,
    SqlCategoryRepository,
    SqlGoalRepository,
    SqlRecurringRepository,
    SqlRefreshTokenRepository,
    SqlTransactionRepository,
    SqlUserRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sessionmaker = sessionmaker

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._sessionmaker()
        self.users = SqlUserRepository(self.session)
        self.tokens = SqlRefreshTokenRepository(self.session)
        self.accounts = SqlAccountRepository(self.session)
        self.categories = SqlCategoryRepository(self.session)
        self.transactions = SqlTransactionRepository(self.session)
        self.budgets = SqlBudgetRepository(self.session)
        self.recurring = SqlRecurringRepository(self.session)
        self.goals = SqlGoalRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None:
                await self.session.rollback()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
