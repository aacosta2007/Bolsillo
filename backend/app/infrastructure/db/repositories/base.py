from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import utcnow

E = TypeVar("E")


class SqlRepo(Generic[E]):
    """Repositorio genérico: mapea dataclass <-> modelo por nombre de campo."""

    model: type
    entity: type[E]
    has_user_id = True

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- mapeo ----
    def to_entity(self, orm: Any) -> E:
        data = {}
        for f in fields(self.entity):  # type: ignore[arg-type]
            if hasattr(orm, f.name):
                data[f.name] = getattr(orm, f.name)
        return self.entity(**data)

    def _columns(self) -> set[str]:
        return {c.key for c in self.model.__table__.columns}  # type: ignore[attr-defined]

    def values(self, e: E) -> dict[str, Any]:
        cols = self._columns()
        out: dict[str, Any] = {}
        for f in fields(e):  # type: ignore[arg-type]
            if f.name in cols:
                v = getattr(e, f.name)
                out[f.name] = v.value if isinstance(v, Enum) else v
        return out

    # ---- CRUD ----
    async def _get_orm(self, user_id: UUID, id: UUID) -> Any | None:
        stmt = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        if self.has_user_id:
            stmt = stmt.where(self.model.user_id == user_id)  # type: ignore[attr-defined]
        return await self.session.scalar(stmt)

    async def get(self, user_id: UUID, id: UUID) -> E | None:
        orm = await self._get_orm(user_id, id)
        return self.to_entity(orm) if orm else None

    async def add(self, entity: E) -> E:
        self.session.add(self.model(**self.values(entity)))
        await self.session.flush()
        return entity

    async def update(self, entity: E) -> E:
        orm = await self.session.get(self.model, entity.id)  # type: ignore[attr-defined]
        for k, v in self.values(entity).items():
            if k in ("id", "created_at"):
                continue
            setattr(orm, k, v)
        orm.updated_at = utcnow()
        await self.session.flush()
        entity.updated_at = orm.updated_at
        return entity

    async def delete(self, user_id: UUID, id: UUID) -> None:
        stmt = delete(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        if self.has_user_id:
            stmt = stmt.where(self.model.user_id == user_id)  # type: ignore[attr-defined]
        await self.session.execute(stmt)
        await self.session.flush()


def ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
