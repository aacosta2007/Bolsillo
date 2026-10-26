from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.notification_triggers import run_daily_notifications
from app.application.recurring import run_pending_for_all_users
from app.core.config import get_settings
from app.infrastructure.db.session import get_sessionmaker
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.push import get_push_sender


def uow_factory() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(get_sessionmaker())


async def recurring_job() -> int:
    return await run_pending_for_all_users(uow_factory, get_push_sender())


async def notifications_job() -> int:
    return await run_daily_notifications(uow_factory, get_push_sender())


def build_scheduler() -> AsyncIOScheduler:
    tz = get_settings().default_timezone
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        recurring_job,
        CronTrigger(hour=0, minute=5, timezone=tz),
        id="recurring-daily",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    # Cada hora en punto: procesa a los usuarios cuya hora local == su notify_hour (la dedupe evita repetir).
    scheduler.add_job(
        notifications_job,
        CronTrigger(minute=0, timezone=tz),
        id="notifications-hourly",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=1800,
    )
    return scheduler
