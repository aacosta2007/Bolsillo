from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, GoalSvc
from app.api.schemas import (
    ContributionCreate,
    ContributionOut,
    GoalCreate,
    GoalOut,
    GoalUpdate,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
async def list_goals(user: CurrentUser, svc: GoalSvc):
    return await svc.list(user.id)


@router.post("", response_model=GoalOut, status_code=201)
async def create_goal(body: GoalCreate, user: CurrentUser, svc: GoalSvc):
    return await svc.create(user.id, body.model_dump())


@router.patch("/{id}", response_model=GoalOut)
async def update_goal(id: UUID, body: GoalUpdate, user: CurrentUser, svc: GoalSvc):
    return await svc.update(user.id, id, body.changes())


@router.delete("/{id}", status_code=204)
async def delete_goal(id: UUID, user: CurrentUser, svc: GoalSvc):
    await svc.delete(user.id, id)
    return Response(status_code=204)


@router.get("/{id}/contributions", response_model=list[ContributionOut])
async def list_contributions(id: UUID, user: CurrentUser, svc: GoalSvc):
    return await svc.contributions(user.id, id)


@router.post("/{id}/contributions", response_model=ContributionOut, status_code=201)
async def add_contribution(id: UUID, body: ContributionCreate, user: CurrentUser, svc: GoalSvc):
    return await svc.add_contribution(user.id, id, body.model_dump())


@router.delete("/{id}/contributions/{cid}", status_code=204)
async def delete_contribution(id: UUID, cid: UUID, user: CurrentUser, svc: GoalSvc):
    await svc.delete_contribution(user.id, id, cid)
    return Response(status_code=204)
