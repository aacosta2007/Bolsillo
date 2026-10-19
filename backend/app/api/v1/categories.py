from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import CategorySvc, CurrentUser
from app.api.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.domain.enums import CategoryKind

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(user: CurrentUser, svc: CategorySvc, kind: CategoryKind | None = None):
    return await svc.list(user.id, kind)


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(body: CategoryCreate, user: CurrentUser, svc: CategorySvc):
    return await svc.create(user.id, body.model_dump())


@router.patch("/{id}", response_model=CategoryOut)
async def update_category(id: UUID, body: CategoryUpdate, user: CurrentUser, svc: CategorySvc):
    return await svc.update(user.id, id, body.changes())


@router.delete("/{id}", status_code=204)
async def delete_category(id: UUID, user: CurrentUser, svc: CategorySvc):
    await svc.delete(user.id, id)
    return Response(status_code=204)
