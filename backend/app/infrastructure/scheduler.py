from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.recurring import run_pending_for_all_users
from app.core.config import get_settings
from app.infrastructure.db.session import get_sessionmaker
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def uow_factory() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(get_sessionmaker())


async def recurring_job() -> int:
    return await run_pending_for_all_users(uow_factory)


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
    return scheduler
