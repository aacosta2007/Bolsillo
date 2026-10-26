from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.deps import CurrentUser, NotificationSvc, SettingsDep
from app.api.schemas import (
    NotificationOut,
    NotificationPage,
    PreferencesOut,
    PreferencesUpdate,
    SubscriptionIn,
    SubscriptionOut,
    TestResult,
    VapidKeyOut,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/vapid-public-key", response_model=VapidKeyOut)
async def vapid_public_key(user: CurrentUser, settings: SettingsDep):
    if not (settings.vapid_public_key and settings.vapid_private_key):
        raise HTTPException(status_code=503, detail="Las notificaciones push no están configuradas en el servidor")
    return VapidKeyOut(public_key=settings.vapid_public_key)


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
async def subscribe(body: SubscriptionIn, user: CurrentUser, svc: NotificationSvc):
    return await svc.subscribe(user.id, body.endpoint, body.keys.p256dh, body.keys.auth, body.device)


@router.delete("/subscriptions", status_code=204)
async def unsubscribe(
    user: CurrentUser, svc: NotificationSvc, endpoint: str = Query(min_length=1, max_length=500)
):
    await svc.unsubscribe(user.id, endpoint)
    return Response(status_code=204)


@router.get("", response_model=NotificationPage)
async def list_notifications(
    user: CurrentUser,
    svc: NotificationSvc,
    unread_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    items, total, unread = await svc.list(user.id, unread_only, page, page_size)
    return NotificationPage(items=items, total=total, page=page, page_size=page_size, unread_count=unread)


@router.post("/read-all", status_code=204)
async def read_all(user: CurrentUser, svc: NotificationSvc):
    await svc.mark_all_read(user.id)
    return Response(status_code=204)


@router.get("/preferences", response_model=PreferencesOut)
async def get_preferences(user: CurrentUser, svc: NotificationSvc):
    return await svc.get_preferences(user.id)


@router.patch("/preferences", response_model=PreferencesOut)
async def update_preferences(body: PreferencesUpdate, user: CurrentUser, svc: NotificationSvc):
    return await svc.update_preferences(user.id, body.changes())


@router.post("/test", response_model=TestResult)
async def send_test(user: CurrentUser, svc: NotificationSvc):
    stats = await svc.send_test(user.id)
    return TestResult(sent=stats.sent, failed=stats.failed)


@router.post("/{id}/read", status_code=204)
async def mark_read(id: UUID, user: CurrentUser, svc: NotificationSvc):
    await svc.mark_read(user.id, id)
    return Response(status_code=204)
