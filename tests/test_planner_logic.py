from datetime import date

import pytest

from planner_logic import occurrence_dates


def test_once_creates_only_selected_date():
    assert occurrence_dates(date(2026, 11, 1), date(2027, 1, 1), "once") == [date(2026, 11, 1)]


def test_daily_is_inclusive():
    assert occurrence_dates(date(2026, 11, 1), date(2026, 11, 3), "daily") == [
        date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)
    ]


def test_weekly_selected_weekdays():
    assert occurrence_dates(date(2026, 11, 2), date(2026, 11, 8), "weekly", [0, 4]) == [
        date(2026, 11, 2), date(2026, 11, 6)
    ]


def test_monthly_skips_missing_day_instead_of_shifting():
    assert occurrence_dates(date(2027, 1, 31), date(2027, 4, 30), "monthly") == [
        date(2027, 1, 31), date(2027, 3, 31)
    ]


def test_invalid_range_and_safety_limit():
    with pytest.raises(ValueError, match="on or after"):
        occurrence_dates(date(2026, 11, 2), date(2026, 11, 1), "daily")
    with pytest.raises(ValueError, match="safety limit"):
        occurrence_dates(date(2026, 1, 1), date(2028, 1, 1), "daily", max_occurrences=10)


def test_weekly_rule_rejects_range_without_selected_day():
    with pytest.raises(ValueError, match="none of the chosen weekdays"):
        occurrence_dates(date(2026, 11, 2), date(2026, 11, 2), "weekly", [1])
