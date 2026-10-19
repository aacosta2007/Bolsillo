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
