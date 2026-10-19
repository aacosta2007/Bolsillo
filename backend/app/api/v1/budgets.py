from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.deps import BudgetSvc, CurrentUser, parse_month
from app.api.schemas import BudgetCopy, BudgetCreate, BudgetStatusOut, BudgetUpdate
from app.application.ports import today_in
from app.domain.rules import first_of_month

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetStatusOut])
async def list_budgets(
    user: CurrentUser,
    svc: BudgetSvc,
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    m = parse_month(month) if month else first_of_month(today_in(user.timezone))
    return await svc.list(user.id, m)


@router.post("", response_model=BudgetStatusOut, status_code=201)
async def create_budget(body: BudgetCreate, user: CurrentUser, svc: BudgetSvc):
    data = body.model_dump()
    data["month"] = parse_month(body.month)
    return await svc.create(user.id, data)


@router.post("/copy", response_model=list[BudgetStatusOut])
async def copy_budgets(body: BudgetCopy, user: CurrentUser, svc: BudgetSvc):
    return await svc.copy(user.id, parse_month(body.from_month), parse_month(body.to_month))


@router.patch("/{id}", response_model=BudgetStatusOut)
async def update_budget(id: UUID, body: BudgetUpdate, user: CurrentUser, svc: BudgetSvc):
    return await svc.update(user.id, id, body.changes())


@router.delete("/{id}", status_code=204)
async def delete_budget(id: UUID, user: CurrentUser, svc: BudgetSvc):
    await svc.delete(user.id, id)
    return Response(status_code=204)
