from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import AccountSvc, CurrentUser
from app.api.schemas import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
async def list_accounts(user: CurrentUser, svc: AccountSvc, include_archived: bool = False):
    return await svc.list(user.id, include_archived)


@router.post("", response_model=AccountOut, status_code=201)
async def create_account(body: AccountCreate, user: CurrentUser, svc: AccountSvc):
    return await svc.create(user.id, body.model_dump())


@router.get("/{id}", response_model=AccountOut)
async def get_account(id: UUID, user: CurrentUser, svc: AccountSvc):
    return await svc.get(user.id, id)


@router.patch("/{id}", response_model=AccountOut)
async def update_account(id: UUID, body: AccountUpdate, user: CurrentUser, svc: AccountSvc):
    return await svc.update(user.id, id, body.changes())


@router.delete("/{id}", status_code=204)
async def delete_account(id: UUID, user: CurrentUser, svc: AccountSvc):
    await svc.delete(user.id, id)
    return Response(status_code=204)
