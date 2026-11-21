"""Deterministic recurrence expansion for Maya Time activity series."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Iterable


def occurrence_dates(
    start_date: date,
    repeat_until: date,
    frequency: str = "once",
    weekdays: Iterable[int] | None = None,
    max_occurrences: int = 732,
) -> list[date]:
    """Expand a recurrence rule into concrete dates, inclusive of both ends.

    Weekly weekdays use Python's convention: Monday=0 ... Sunday=6.
    Monthly recurrences use the same day-of-month; months without that day
    (e.g. the 31st in April) are skipped rather than shifted silently.
    """
    if repeat_until < start_date:
        raise ValueError("Repeat-until date must be on or after the start date.")
    frequency = frequency.strip().lower()
    if frequency not in {"once", "daily", "weekly", "monthly"}:
        raise ValueError("Frequency must be once, daily, weekly, or monthly.")
    if frequency == "once":
        return [start_date]

    selected_weekdays = set(weekdays or [start_date.weekday()])
    if any(day < 0 or day > 6 for day in selected_weekdays):
        raise ValueError("Weekdays must use values from 0 (Monday) to 6 (Sunday).")

    results: list[date] = []
    if frequency in {"daily", "weekly"}:
        day = start_date
        while day <= repeat_until:
            include = frequency == "daily" or day.weekday() in selected_weekdays
            if include:
                results.append(day)
            day += timedelta(days=1)
            if len(results) > max_occurrences:
                raise ValueError(f"Recurrence exceeds the {max_occurrences}-occurrence safety limit.")
        if frequency == "weekly" and not results:
            raise ValueError("The selected date range contains none of the chosen weekdays.")
        return results

    year, month = start_date.year, start_date.month
    anchor_day = start_date.day
    while (year, month) <= (repeat_until.year, repeat_until.month):
        last_day = calendar.monthrange(year, month)[1]
        if anchor_day <= last_day:
            candidate = date(year, month, anchor_day)
            if start_date <= candidate <= repeat_until:
                results.append(candidate)
        month += 1
        if month == 13:
            year += 1
            month = 1
        if len(results) > max_occurrences:
            raise ValueError(f"Recurrence exceeds the {max_occurrences}-occurrence safety limit.")
    return results
