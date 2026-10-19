from __future__ import annotations

from uuid import UUID

from app.domain.entities import Category
from app.domain.enums import CategoryKind
from app.domain.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.domain.repositories import UnitOfWork


class CategoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list(self, user_id: UUID, kind: CategoryKind | None = None) -> list[Category]:
        return await self.uow.categories.list(user_id, kind)

    async def get(self, user_id: UUID, id: UUID) -> Category:
        cat = await self.uow.categories.get(user_id, id)
        if cat is None:
            raise NotFoundError("Categoría no encontrada")
        return cat

    async def _check_parent(self, user_id: UUID, kind: CategoryKind, parent_id: UUID | None, self_id: UUID | None):
        if parent_id is None:
            return
        if parent_id == self_id:
            raise BusinessRuleError("Una categoría no puede ser su propia categoría padre")
        parent = await self.get(user_id, parent_id)
        if parent.kind != kind:
            raise BusinessRuleError("La categoría padre debe ser del mismo tipo")

    async def create(self, user_id: UUID, data: dict) -> Category:
        kind = CategoryKind(data["kind"])
        if await self.uow.categories.name_exists(user_id, kind, data["name"]):
            raise ConflictError("Ya existe una categoría con ese nombre")
        await self._check_parent(user_id, kind, data.get("parent_id"), None)
        cat = Category(
            user_id=user_id,
            name=data["name"],
            kind=kind,
            parent_id=data.get("parent_id"),
            **{k: data[k] for k in ("icon", "color") if data.get(k)},
        )
        await self.uow.categories.add(cat)
        await self.uow.commit()
        return cat

    async def update(self, user_id: UUID, id: UUID, changes: dict) -> Category:
        cat = await self.get(user_id, id)
        if "kind" in changes and changes["kind"] is not None and CategoryKind(changes["kind"]) != cat.kind:
            if await self.uow.categories.in_use(user_id, id):
                raise ConflictError("No se puede cambiar el tipo de una categoría con movimientos")
            cat.kind = CategoryKind(changes["kind"])
        for key in ("name", "icon", "color"):
            if changes.get(key) is not None:
                setattr(cat, key, changes[key])
        if "parent_id" in changes:
            await self._check_parent(user_id, cat.kind, changes["parent_id"], cat.id)
            cat.parent_id = changes["parent_id"]
        if await self.uow.categories.name_exists(user_id, cat.kind, cat.name, exclude_id=cat.id):
            raise ConflictError("Ya existe una categoría con ese nombre")
        await self.uow.categories.update(cat)
        await self.uow.commit()
        return cat

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self.get(user_id, id)
        if await self.uow.categories.in_use(user_id, id):
            raise ConflictError("La categoría tiene movimientos, presupuestos o recurrentes asociados")
        await self.uow.categories.delete(user_id, id)
        await self.uow.commit()
