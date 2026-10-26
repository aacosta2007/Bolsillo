"""Bandeja de avisos, preferencias, suscripciones push y envío."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from app.application.ports import PushResult, PushSender, PushTarget
from app.domain import notification_texts as texts
from app.domain.entities import Notification, PushSubscription, User, utcnow
from app.domain.enums import NotificationKind
from app.domain.exceptions import BusinessRuleError, NotFoundError
from app.domain.repositories import UnitOfWork

log = logging.getLogger(__name__)

PREF_FIELDS = (
    "budget_alerts", "upcoming_alerts", "upcoming_days_before",
    "payday_alerts", "monthly_report_alerts", "notify_hour",
)
# Preferencia que controla cada tipo (los de prueba siempre pasan)
KIND_PREF = {
    NotificationKind.BUDGET_WARNING: "budget_alerts",
    NotificationKind.BUDGET_EXCEEDED: "budget_alerts",
    NotificationKind.UPCOMING_RECURRING: "upcoming_alerts",
    NotificationKind.PAYDAY: "payday_alerts",
    NotificationKind.MONTHLY_REPORT: "monthly_report_alerts",
}


@dataclass(frozen=True)
class SendStats:
    sent: int = 0
    failed: int = 0


class NotificationService:
    def __init__(self, uow: UnitOfWork, sender: PushSender):
        self.uow = uow
        self.sender = sender

    # ---- bandeja ----
    async def list(
        self, user_id: UUID, unread_only: bool, page: int, page_size: int
    ) -> tuple[list[Notification], int, int]:
        items, total = await self.uow.notifications.list(user_id, unread_only, page, page_size)
        return items, total, await self.uow.notifications.unread_count(user_id)

    async def mark_read(self, user_id: UUID, id: UUID) -> None:
        if await self.uow.notifications.get(user_id, id) is None:
            raise NotFoundError("Aviso no encontrado")
        await self.uow.notifications.mark_read(user_id, id)
        await self.uow.commit()

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.uow.notifications.mark_all_read(user_id)
        await self.uow.commit()

    # ---- preferencias ----
    async def _user(self, user_id: UUID) -> User:
        user = await self.uow.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuario no encontrado")
        return user

    async def get_preferences(self, user_id: UUID) -> User:
        return await self._user(user_id)

    async def update_preferences(self, user_id: UUID, changes: dict) -> User:
        user = await self._user(user_id)
        if "upcoming_days_before" in changes and not 0 <= changes["upcoming_days_before"] <= 7:
            raise BusinessRuleError("Los días de anticipación deben estar entre 0 y 7")
        if "notify_hour" in changes and not 0 <= changes["notify_hour"] <= 23:
            raise BusinessRuleError("La hora de aviso debe estar entre 0 y 23")
        for key in PREF_FIELDS:
            if changes.get(key) is not None:
                setattr(user, key, changes[key])
        user.updated_at = utcnow()
        await self.uow.users.update(user)
        await self.uow.commit()
        return user

    # ---- suscripciones ----
    async def subscribe(
        self, user_id: UUID, endpoint: str, p256dh: str, auth: str, device: str | None
    ) -> PushSubscription:
        sub = await self.uow.push_subscriptions.upsert(
            PushSubscription(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth, device=device)
        )
        await self.uow.commit()
        return sub

    async def unsubscribe(self, user_id: UUID, endpoint: str) -> None:
        await self.uow.push_subscriptions.delete_by_endpoint(user_id, endpoint)
        await self.uow.commit()

    # ---- creación y envío ----
    async def notify(
        self, user_id: UUID, kind: NotificationKind, dedupe_key: str, title: str, body: str, url: str = "/"
    ) -> Notification | None:
        """Crea el aviso en la bandeja y lo envía por push. Devuelve None si el tipo está
        desactivado o ya existía (dedupe). Un fallo de push no afecta a la bandeja."""
        pref = KIND_PREF.get(kind)
        if pref is not None:
            user = await self._user(user_id)
            if not getattr(user, pref):
                return None
        note = Notification(
            user_id=user_id, kind=kind.value, title=title, body=body, url=url, dedupe_key=dedupe_key
        )
        if not await self.uow.notifications.try_add(note):
            return None
        await self.uow.commit()
        await self._push(note)
        return note

    async def notify_message(
        self, user_id: UUID, kind: NotificationKind, dedupe_key: str, msg: texts.Message
    ) -> Notification | None:
        return await self.notify(user_id, kind, dedupe_key, msg.title, msg.body, msg.url)

    async def _push(self, note: Notification) -> SendStats:
        if not self.sender.enabled:
            return SendStats()
        try:
            subs = await self.uow.push_subscriptions.list_for_user(note.user_id)
            payload = {
                "title": note.title, "body": note.body, "url": note.url,
                "tag": f"{note.kind}:{note.dedupe_key}", "notification_id": str(note.id),
            }
            sent = failed = 0
            for sub in subs:
                result = await self.sender.send(PushTarget(sub.endpoint, sub.p256dh, sub.auth), payload)
                if result == PushResult.OK:
                    sent += 1
                    continue
                failed += 1
                if result == PushResult.GONE:
                    await self.uow.push_subscriptions.delete(sub.id)
                    await self.uow.commit()
            return SendStats(sent, failed)
        except Exception:  # el push nunca debe romper la petición del usuario
            log.exception("Fallo enviando push al usuario %s", note.user_id)
            return SendStats()

    async def send_test(self, user_id: UUID) -> SendStats:
        msg = texts.test_message()
        key = f"test:{utcnow().strftime('%Y%m%d%H%M%S%f')}"
        note = Notification(
            user_id=user_id, kind=NotificationKind.TEST.value, title=msg.title, body=msg.body,
            url=msg.url, dedupe_key=key,
        )
        await self.uow.notifications.try_add(note)
        await self.uow.commit()
        return await self._push(note)
