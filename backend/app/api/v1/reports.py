from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, ReportSvc
from app.api.schemas import (
    CategoryReportCountOut,
    DashboardOut,
    PayPeriodOut,
    TrendNetOut,
)
from app.domain.enums import TransactionType

router = APIRouter(tags=["reports"])


@router.get("/dashboard/summary", response_model=DashboardOut)
async def dashboard_summary(
    user: CurrentUser,
    svc: ReportSvc,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
):
    d = await svc.dashboard(user.id, date_from, date_to)
    data = asdict(d)
    data["period"] = {"from": data.pop("period_from"), "to": data.pop("period_to")}
    return data


@router.get("/reports/by-category", response_model=list[CategoryReportCountOut])
async def by_category(
    user: CurrentUser,
    svc: ReportSvc,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    type: TransactionType = TransactionType.EXPENSE,
):
    return await svc.by_category(user.id, date_from, date_to, type)


@router.get("/reports/monthly-trend", response_model=list[TrendNetOut])
async def monthly_trend(user: CurrentUser, svc: ReportSvc, months: int = Query(default=12, ge=1, le=60)):
    return await svc.monthly_trend(user.id, months)


@router.get("/reports/pay-periods", response_model=list[PayPeriodOut])
async def pay_periods(user: CurrentUser, svc: ReportSvc, count: int = Query(default=6, ge=1, le=24)):
    return await svc.pay_periods(user.id, count)


@router.get("/export/csv")
async def export_csv(
    user: CurrentUser,
    svc: ReportSvc,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
):
    content, start, end = await svc.export_csv(user.id, date_from, date_to)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="bolsillo_{start}_{end}.csv"'},
    )
