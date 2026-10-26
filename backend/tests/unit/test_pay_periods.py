from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.entities import RecurringRule
from app.domain.enums import Frequency, TransactionType, WeekendAdjust
from app.domain.pay_periods import (
    PeriodSource,
    PeriodSpan,
    build_spans,
    paydays,
    period_metrics,
)

D = Decimal


def rule(days="15,L", start=date(2026, 10, 1), adjust=WeekendAdjust.PREVIOUS_BUSINESS_DAY, amount="1000000", **kw):
    return RecurringRule(
        user_id=uuid4(), type=TransactionType.INCOME, amount=D(amount), account_id=uuid4(), category_id=uuid4(),
        frequency=Frequency.MONTHLY_DAYS, days_of_month=days, start_date=start, next_run_date=start,
        weekend_adjust=adjust, is_paycheck=True, **kw,
    )


def spans(rules, today, count):
    dates = [p.date for p in paydays(rules, today)]
    return [(s.start, s.end, s.source.value) for s in build_spans(dates, today, count)]


def test_paydays_with_weekend_adjust_and_periods():
    # 2026-10-31 sábado -> vie 30; 2026-11-15 domingo -> vie 13; 2026-11-30 lunes
    today = date(2026, 11, 20)
    assert [p.date for p in paydays([rule()], today)] == [
        date(2026, 10, 15), date(2026, 10, 30), date(2026, 11, 13), date(2026, 11, 30)]
    assert spans([rule()], today, 3) == [
        (date(2026, 11, 13), date(2026, 11, 29), "paycheck"),
        (date(2026, 10, 30), date(2026, 11, 12), "paycheck"),
        (date(2026, 10, 15), date(2026, 10, 29), "paycheck"),
    ]


def test_seventeen_day_period():
    # 2026-08-15 sábado -> vie 14; 2026-08-31 lunes
    got = spans([rule(start=date(2026, 8, 1))], date(2026, 8, 20), 1)
    assert got == [(date(2026, 8, 14), date(2026, 8, 30), "paycheck")]
    assert (got[0][1] - got[0][0]).days + 1 == 17


def test_calendar_fallback_without_paycheck_and_before_first_payday():
    assert spans([], date(2026, 10, 25), 3) == [
        (date(2026, 10, 16), date(2026, 10, 31), "calendar"),
        (date(2026, 10, 1), date(2026, 10, 15), "calendar"),
        (date(2026, 9, 16), date(2026, 9, 30), "calendar"),
    ]
    # hoy antes del primer pago (15 oct): calendario recortado; no se solapa con el primer periodo
    r = rule(start=date(2026, 10, 15))
    assert spans([r], date(2026, 10, 10), 2) == [
        (date(2026, 10, 1), date(2026, 10, 14), "calendar"),
        (date(2026, 9, 16), date(2026, 9, 30), "calendar"),
    ]
    # periodos de sueldo y, antes del primero, calendario recortado
    assert spans([r], date(2026, 10, 20), 2) == [
        (date(2026, 10, 15), date(2026, 10, 29), "paycheck"),
        (date(2026, 10, 1), date(2026, 10, 14), "calendar"),
    ]


def test_two_paycheck_rules_same_day_single_date_and_summed_amount():
    pd = paydays([rule(amount="600000"), rule(days="15", amount="400000", adjust=WeekendAdjust.NONE)],
                 date(2026, 10, 20))
    first = [p for p in pd if p.date == date(2026, 10, 15)]
    assert len(first) == 1 and first[0].amount == D("1000000")
    assert len({p.date for p in pd}) == len(pd)


def test_inactive_non_paycheck_and_end_date_rules_are_ignored():
    inactive = rule(active=False)
    other = rule()
    other.is_paycheck = False
    assert paydays([inactive, other], date(2026, 10, 20)) == []
    ended = rule(end_date=date(2026, 10, 20))
    assert [p.date for p in paydays([ended], date(2026, 12, 1))] == [date(2026, 10, 15)]
    # sin siguiente pago el periodo en curso cierra con el calendario
    assert spans([ended], date(2026, 10, 18), 1) == [(date(2026, 10, 15), date(2026, 10, 31), "paycheck")]


def span(start=date(2026, 10, 15), end=date(2026, 10, 29)):
    return PeriodSpan(start=start, end=end, source=PeriodSource.PAYCHECK)


def test_metrics_in_progress():
    p = period_metrics(span(), date(2026, 10, 20), D("1350000"), D("612400"))
    assert (p.days, p.days_elapsed, p.days_remaining, p.in_progress) == (15, 6, 10, True)
    assert p.net == D("737600.00") and p.spent_per_day == D("102066.67")
    assert p.available_per_day == D("73760.00")
    assert (p.spent_percent, p.time_percent, p.status.value) == (45.4, 40.0, "en_curso")


def test_metrics_closed_statuses():
    end = date(2026, 11, 5)
    saving = period_metrics(span(), end, D("1000"), D("500"))
    tight = period_metrics(span(), end, D("1000"), D("950"))
    deficit = period_metrics(span(), end, D("1000"), D("1200"))
    assert [saving.status.value, tight.status.value, deficit.status.value] == ["ahorro", "justo", "deficit"]
    assert (saving.days_elapsed, saving.days_remaining, saving.available_per_day) == (15, 0, None)
    assert saving.time_percent == 100.0 and saving.spent_per_day == D("33.33")
    assert period_metrics(span(), end, D("1000"), D("900")).status.value == "ahorro"  # net = 10 % exacto


def test_available_per_day_is_zero_with_negative_net_and_zero_income_percent():
    p = period_metrics(span(), date(2026, 10, 15), D("0"), D("5000"))
    assert p.net == D("-5000.00") and p.available_per_day == D("0.00")
    assert p.spent_percent == 0.0 and (p.days_elapsed, p.days_remaining) == (1, 15)
