from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, TransactionSvc
from app.api.schemas import Page, TransactionCreate, TransactionOut, TransactionUpdate
from app.domain.entities import TransactionFilters
from app.domain.enums import TransactionType

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=Page[TransactionOut])
async def list_transactions(
    user: CurrentUser,
    svc: TransactionSvc,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    type: TransactionType | None = None,
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    filters = TransactionFilters(
        date_from=date_from, date_to=date_to, account_id=account_id,
        category_id=category_id, type=type, q=q or None,
    )
    items, total = await svc.list(user.id, filters, page, page_size)
    return Page[TransactionOut](items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TransactionOut, status_code=201)
async def create_transaction(body: TransactionCreate, user: CurrentUser, svc: TransactionSvc):
    return await svc.create(user.id, body.model_dump())


@router.get("/{id}", response_model=TransactionOut)
async def get_transaction(id: UUID, user: CurrentUser, svc: TransactionSvc):
    return await svc.get(user.id, id)


@router.patch("/{id}", response_model=TransactionOut)
async def update_transaction(
    id: UUID, body: TransactionUpdate, user: CurrentUser, svc: TransactionSvc
):
    return await svc.update(user.id, id, body.changes())


@router.delete("/{id}", status_code=204)
async def delete_transaction(id: UUID, user: CurrentUser, svc: TransactionSvc):
    await svc.delete(user.id, id)
    return Response(status_code=204)
