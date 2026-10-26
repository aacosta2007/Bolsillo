from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, NotificationTriggersDep, RecurringSvc
from app.api.schemas import (
    RecurringCreate,
    RecurringOut,
    RecurringUpdate,
    RunResult,
    UpcomingOut,
)
from app.application.ports import today_in

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", response_model=list[RecurringOut])
async def list_rules(user: CurrentUser, svc: RecurringSvc):
    return await svc.list(user.id)


@router.post("", response_model=RecurringOut, status_code=201)
async def create_rule(body: RecurringCreate, user: CurrentUser, svc: RecurringSvc):
    return await svc.create(user.id, body.model_dump())


@router.post("/run", response_model=RunResult)
async def run_rules(user: CurrentUser, svc: RecurringSvc, triggers: NotificationTriggersDep):
    created = await svc.run(user.id, today_in(user.timezone))
    if svc.paychecks:
        await triggers.paychecks_generated(user, svc.paychecks)  # aviso "payday"; nunca falla la petición
    return RunResult(created=created)


@router.get("/upcoming", response_model=list[UpcomingOut])
async def upcoming(user: CurrentUser, svc: RecurringSvc, days: int = Query(default=30, ge=1, le=366)):
    return await svc.upcoming(user.id, days, today_in(user.timezone))


@router.patch("/{id}", response_model=RecurringOut)
async def update_rule(id: UUID, body: RecurringUpdate, user: CurrentUser, svc: RecurringSvc):
    return await svc.update(user.id, id, body.changes())


@router.delete("/{id}", status_code=204)
async def delete_rule(id: UUID, user: CurrentUser, svc: RecurringSvc):
    await svc.delete(user.id, id)
    return Response(status_code=204)
