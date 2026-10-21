from datetime import date
from decimal import Decimal

from app.domain.enums import BudgetState, Frequency
from app.domain.rules import (
    budget_status,
    goal_percent,
    monthly_needed,
    next_after,
    occurrence,
)

D = Decimal


def test_monthly_day_31_clamps_to_end_of_month_without_drifting():
    start = date(2026, 1, 31)
    seq = []
    cur = start
    for _ in range(5):
        seq.append(cur)
        cur = next_after(start, Frequency.MONTHLY, 1, cur)
    assert seq == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30), date(2026, 5, 31)]


def test_monthly_leap_year_and_interval():
    start = date(2028, 1, 31)
    assert next_after(start, Frequency.MONTHLY, 1, start) == date(2028, 2, 29)
    assert next_after(date(2026, 1, 15), Frequency.MONTHLY, 3, date(2026, 1, 15)) == date(2026, 4, 15)


def test_daily_weekly_yearly():
    assert next_after(date(2026, 1, 1), Frequency.DAILY, 1, date(2026, 1, 1)) == date(2026, 1, 2)
    assert next_after(date(2026, 1, 1), Frequency.DAILY, 10, date(2026, 1, 1)) == date(2026, 1, 11)
    assert next_after(date(2026, 1, 5), Frequency.WEEKLY, 2, date(2026, 1, 5)) == date(2026, 1, 19)
    assert next_after(date(2024, 2, 29), Frequency.YEARLY, 1, date(2024, 2, 29)) == date(2025, 2, 28)
    assert next_after(date(2024, 2, 29), Frequency.YEARLY, 4, date(2024, 2, 29)) == date(2028, 2, 29)


def test_next_after_skips_ahead_from_far_past_and_before_start():
    assert next_after(date(2020, 1, 1), Frequency.DAILY, 1, date(2026, 10, 18)) == date(2026, 10, 19)
    assert next_after(date(2020, 1, 31), Frequency.MONTHLY, 1, date(2026, 10, 18)) == date(2026, 10, 31)
    assert next_after(date(2026, 5, 1), Frequency.MONTHLY, 1, date(2026, 1, 1)) == date(2026, 5, 1)
    assert occurrence(date(2026, 1, 31), Frequency.MONTHLY, 1, 1) == date(2026, 2, 28)


def test_budget_status_thresholds():
    rem, pct, st = budget_status(D("600000"), D("510000"), D("0.80"))
    assert (rem, pct, st) == (D("90000"), 85.0, BudgetState.WARNING)
    assert budget_status(D("100"), D("79.99"), D("0.80"))[2] == BudgetState.OK
    assert budget_status(D("100"), D("80"), D("0.80"))[2] == BudgetState.WARNING
    assert budget_status(D("100"), D("100"), D("0.80"))[2] == BudgetState.WARNING  # igual al límite no excede
    rem, pct, st = budget_status(D("100"), D("100.01"), D("0.80"))
    assert st == BudgetState.EXCEEDED and rem == D("-0.01")
    assert budget_status(D("100"), D("0"), D("0.8")) == (D("100"), 0.0, BudgetState.OK)


def test_monthly_needed():
    today = date(2026, 10, 18)
    assert monthly_needed(D("3000000"), D("750000"), date(2027, 6, 1), today) == D("281250.00")  # 8 meses
    assert monthly_needed(D("1000"), D("0"), date(2026, 10, 30), today) == D("1000.00")  # mínimo 1 mes
    assert monthly_needed(D("1000"), D("0"), date(2026, 1, 1), today) == D("1000.00")  # fecha vencida
    assert monthly_needed(D("1000"), D("0"), None, today) is None
    assert monthly_needed(D("1000"), D("1000"), date(2027, 1, 1), today) is None
    assert monthly_needed(D("100"), D("0"), date(2027, 1, 18), today) == D("33.33")  # 3 meses
    assert monthly_needed(D("100"), D("0"), date(2027, 2, 1), today) == D("25.00")  # 4 meses


def test_goal_percent():
    assert goal_percent(D("3000000"), D("750000")) == 25.0
    assert goal_percent(D("3"), D("1")) == 33.3


# ---------- monthly_days ----------
import pytest  # noqa: E402

from app.domain.enums import WeekendAdjust  # noqa: E402
from app.domain.exceptions import BusinessRuleError  # noqa: E402
from app.domain.rules import (  # noqa: E402
    effective_date,
    first_nominal_on_or_after,
    month_occurrences,
    monthly_equivalent,
    next_nominal_after,
    normalize_days_of_month,
    parse_days_of_month,
)

MD = Frequency.MONTHLY_DAYS


def occ(y, m, raw):
    return month_occurrences(y, m, parse_days_of_month(raw))


def test_quincenal_15_and_last_across_month_lengths():
    assert occ(2026, 10, "15,L") == [date(2026, 10, 15), date(2026, 10, 31)]  # 31 días
    assert occ(2026, 11, "15,L") == [date(2026, 11, 15), date(2026, 11, 30)]  # 30 días
    assert occ(2027, 2, "15,L") == [date(2027, 2, 15), date(2027, 2, 28)]
    assert occ(2028, 2, "15,L") == [date(2028, 2, 15), date(2028, 2, 29)]  # bisiesto


def test_days_beyond_month_end_are_clamped_and_deduplicated():
    assert occ(2027, 2, "15,30") == [date(2027, 2, 15), date(2027, 2, 28)]
    assert occ(2027, 2, "30,L") == [date(2027, 2, 28)]  # una sola ocurrencia
    assert occ(2026, 4, "31") == [date(2026, 4, 30)]
    assert occ(2026, 1, "31,L") == [date(2026, 1, 31)]


def test_days_of_month_parse_and_normalize():
    assert normalize_days_of_month("L,15") == "15,L"
    assert normalize_days_of_month(" 20 , 5 , l ") == "5,20,L"
    assert normalize_days_of_month("5") == "5"
    assert parse_days_of_month("1,31,L") == (1, 31, 32)


@pytest.mark.parametrize("raw", ["0", "32", "15,15", "1,2,3,4", "x", "", "15,,L", "-1", "1.5", None, "L,L"])
def test_days_of_month_invalid(raw):
    with pytest.raises(BusinessRuleError):
        parse_days_of_month(raw)


def test_effective_date_weekend_adjust():
    prev = WeekendAdjust.PREVIOUS_BUSINESS_DAY
    assert date(2026, 11, 15).weekday() == 6 and date(2027, 1, 31).weekday() == 6  # domingos
    assert effective_date(date(2026, 11, 15), prev) == date(2026, 11, 13)  # domingo -> viernes
    assert effective_date(date(2027, 1, 31), prev) == date(2027, 1, 29)
    assert effective_date(date(2026, 10, 31), prev) == date(2026, 10, 30)  # sábado -> viernes
    assert effective_date(date(2026, 10, 15), prev) == date(2026, 10, 15)  # jueves, sin cambio
    assert effective_date(date(2026, 11, 15), WeekendAdjust.NONE) == date(2026, 11, 15)
    assert effective_date(date(2026, 11, 15), "none") == date(2026, 11, 15)


def test_first_and_next_nominal_monthly_days():
    start = date(2026, 9, 1)
    first = first_nominal_on_or_after(start, MD, 1, "15,L", start)
    assert first == date(2026, 9, 15)
    seq, cur = [first], first
    for _ in range(4):
        cur = next_nominal_after(start, MD, 1, "15,L", cur)
        seq.append(cur)
    assert seq == [date(2026, 9, 15), date(2026, 9, 30), date(2026, 10, 15), date(2026, 10, 31), date(2026, 11, 15)]
    assert first_nominal_on_or_after(start, MD, 1, "15,L", date(2026, 9, 30)) == date(2026, 9, 30)
    assert first_nominal_on_or_after(start, MD, 1, "15,L", date(2026, 12, 16)) == date(2026, 12, 31)
    assert first_nominal_on_or_after(start, MD, 1, "15,L", date(2025, 1, 1)) == date(2026, 9, 15)  # >= start
    assert next_nominal_after(date(2026, 1, 1), MD, 1, "5", date(2026, 12, 5)) == date(2027, 1, 5)  # cruza de año


def test_first_and_next_nominal_classic_frequencies():
    start = date(2026, 1, 31)
    assert first_nominal_on_or_after(start, Frequency.MONTHLY, 1, None, start) == start
    assert first_nominal_on_or_after(start, Frequency.MONTHLY, 1, None, date(2026, 2, 1)) == date(2026, 2, 28)
    assert first_nominal_on_or_after(start, Frequency.MONTHLY, 1, None, date(2025, 1, 1)) == start
    assert next_nominal_after(start, Frequency.MONTHLY, 1, None, start) == date(2026, 2, 28)
    assert next_nominal_after(date(2026, 1, 1), Frequency.DAILY, 3, None, date(2026, 1, 1)) == date(2026, 1, 4)


def test_monthly_equivalent():
    assert monthly_equivalent(D("1000000"), MD, 1, "15,L") == D("2000000.00")
    assert monthly_equivalent(D("500"), MD, 1, "5") == D("500.00")
    assert monthly_equivalent(D("39900"), Frequency.MONTHLY, 1, None) == D("39900.00")
    assert monthly_equivalent(D("300"), Frequency.MONTHLY, 3, None) == D("100.00")
    assert monthly_equivalent(D("100"), Frequency.WEEKLY, 1, None) == D("433.33")
    assert monthly_equivalent(D("100"), Frequency.WEEKLY, 2, None) == D("216.67")
    assert monthly_equivalent(D("10"), Frequency.DAILY, 1, None) == D("304.17")
    assert monthly_equivalent(D("1200"), Frequency.YEARLY, 1, None) == D("100.00")
    assert monthly_equivalent(D("1200"), Frequency.YEARLY, 2, None) == D("50.00")
