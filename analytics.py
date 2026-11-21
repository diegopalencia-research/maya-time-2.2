"""Small, descriptive analytics for personal time-use records."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def tasks_to_frame(tasks: list[dict[str, Any]]) -> pd.DataFrame:
    columns = [
        "id", "event_date", "start_time", "end_time", "title", "category",
        "priority", "deadline", "completed", "notes", "minutes", "weekday", "hour",
    ]
    if not tasks:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(tasks).copy()
    start = pd.to_datetime(frame["event_date"] + " " + frame["start_time"])
    end = pd.to_datetime(frame["event_date"] + " " + frame["end_time"])
    frame["minutes"] = (end - start).dt.total_seconds() / 60
    frame["weekday"] = start.dt.dayofweek
    frame["hour"] = start.dt.hour
    frame["completed"] = frame["completed"].astype(bool)
    return frame


def time_by_category(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["category", "hours"])
    result = frame.groupby("category", as_index=False)["minutes"].sum()
    result["hours"] = result["minutes"] / 60
    return result.sort_values("hours", ascending=False)


def time_by_weekday(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["weekday", "day", "hours"])
    result = frame.groupby("weekday", as_index=False)["minutes"].sum()
    result["hours"] = result["minutes"] / 60
    result["day"] = result["weekday"].map(lambda value: WEEKDAYS[int(value)])
    return result.sort_values("weekday")


def activity_heatmap(frame: pd.DataFrame) -> pd.DataFrame:
    """Allocate each scheduled task's minutes to the hour cells it overlaps."""
    matrix = pd.DataFrame(0.0, index=WEEKDAYS, columns=range(24))
    if frame.empty:
        return matrix

    for row in frame.itertuples(index=False):
        # Supabase/PostgreSQL time columns may include seconds; pandas parses
        # both HH:MM and HH:MM:SS consistently.
        start = pd.to_datetime(f"{row.event_date} {row.start_time}").to_pydatetime()
        end = pd.to_datetime(f"{row.event_date} {row.end_time}").to_pydatetime()
        cursor = start
        day_label = WEEKDAYS[cursor.weekday()]
        while cursor < end:
            next_hour = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            segment_end = min(next_hour, end)
            matrix.loc[day_label, cursor.hour] += (segment_end - cursor).total_seconds() / 60
            cursor = segment_end
    return matrix


def summary_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    if frame.empty:
        return {"tasks": 0, "planned_hours": 0.0, "completed": 0, "completion_rate": 0.0}
    total = len(frame)
    completed = int(frame["completed"].sum())
    return {
        "tasks": total,
        "planned_hours": float(frame["minutes"].sum() / 60),
        "completed": completed,
        "completion_rate": float(completed / total * 100),
    }


def demo_tasks(start_date, end_date) -> list[dict[str, Any]]:
    """Deterministic synthetic records used only by the public demo."""
    from datetime import timedelta

    rows: list[dict[str, Any]] = []
    task_id = 1
    day = start_date
    patterns = {
        0: [("Research", "Evidence review", "08:00", "09:30"), ("Work", "Operations", "13:00", "17:00")],
        1: [("Development", "Calendar engine", "08:00", "09:30"), ("Work", "Operations", "13:00", "17:00")],
        2: [("Rest", "Recovery block", "09:00", "10:00")],
        3: [("Writing", "Research notes", "08:00", "09:30"), ("Work", "Operations", "13:00", "17:00")],
        4: [("Analysis", "Weekly review", "08:00", "09:00"), ("Work", "Operations", "13:00", "17:00")],
        5: [("Learning", "Independent study", "09:00", "10:30")],
        6: [("Planning", "Weekly preparation", "17:00", "17:45")],
    }
    while day <= end_date:
        for index, (category, title, start, end) in enumerate(patterns[day.weekday()]):
            rows.append({
                "id": task_id,
                "event_date": day.isoformat(),
                "start_time": start,
                "end_time": end,
                "title": title,
                "category": category,
                "priority": 2 if index == 0 else 3,
                "deadline": None,
                "completed": (day.toordinal() + index) % 3 != 0,
                "notes": "Synthetic portfolio demonstration record.",
            })
            task_id += 1
        day += timedelta(days=1)
    return rows
