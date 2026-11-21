from datetime import date
import sqlite3

import pytest

from storage import SQLiteStore


def test_activity_crud_and_reflection_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "maya_time_test.sqlite3")
    task_id = store.create_activity(
        start_date=date(2026, 11, 2),
        start_time="08:00",
        end_time="09:30",
        title="Research block",
        category="Research",
        priority=1,
        deadline=date(2026, 11, 6),
        notes="Test record",
    )
    rows = store.get_tasks(date(2026, 11, 2), date(2026, 11, 2))
    assert len(rows) == 1
    assert rows[0]["id"] == task_id
    assert rows[0]["title"] == "Research block"
    assert rows[0]["completed"] == 0
    assert rows[0]["frequency"] == "once"

    store.set_task_completed(task_id, True)
    assert store.get_tasks(date(2026, 11, 2), date(2026, 11, 2))[0]["completed"] == 1

    store.save_reflection(date(2026, 11, 2), "Focused", 4, "Finished the outline")
    reflection = store.get_reflection(date(2026, 11, 2))
    assert reflection is not None
    assert reflection["mood"] == "Focused"
    assert reflection["energy"] == 4

    store.delete_task(task_id)
    assert store.get_tasks(date(2026, 11, 2), date(2026, 11, 2)) == []


def test_activity_rejects_invalid_time_range(tmp_path):
    store = SQLiteStore(tmp_path / "maya_time_test.sqlite3")
    with pytest.raises(ValueError, match="End time"):
        store.create_activity(
            start_date=date(2026, 11, 2),
            start_time="09:00",
            end_time="09:00",
            title="Invalid block",
            category="Other",
        )


def test_repeating_activity_creates_one_series_and_multiple_occurrences(tmp_path):
    store = SQLiteStore(tmp_path / "recurrence.sqlite3")
    store.create_activity(
        start_date=date(2026, 11, 2), start_time="08:00", end_time="09:00",
        title="Study", category="Learning", frequency="weekly",
        repeat_until=date(2026, 11, 16), weekdays=[0, 2],
    )
    tasks = store.get_tasks(date(2026, 11, 1), date(2026, 11, 30))
    assert [row["event_date"] for row in tasks] == [
        "2026-11-02", "2026-11-04", "2026-11-09", "2026-11-11", "2026-11-16"
    ]
    assert len({row["series_id"] for row in tasks}) == 1
    assert len(store.get_all_series()) == 1

    store.update_series(tasks[0]["series_id"], title="Updated study")
    assert all(row["title"] == "Updated study" for row in store.get_tasks(date(2026, 11, 1), date(2026, 11, 30)))

    store.delete_series(tasks[0]["series_id"])
    assert store.get_tasks(date(2026, 11, 1), date(2026, 11, 30)) == []


def test_legacy_tasks_are_migrated_once(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("""CREATE TABLE tasks (
            id INTEGER PRIMARY KEY, event_date TEXT, start_time TEXT, end_time TEXT,
            title TEXT, category TEXT, priority INTEGER, deadline TEXT,
            completed INTEGER, notes TEXT, created_at TEXT
        )""")
        connection.execute(
            "INSERT INTO tasks VALUES (1,'2026-10-31','08:00','09:00','Old task','Research',2,NULL,1,'legacy',CURRENT_TIMESTAMP)"
        )
    store = SQLiteStore(db_path)
    tasks = store.get_tasks(date(2026, 10, 31), date(2026, 10, 31))
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Old task"
    assert tasks[0]["completed"] == 1
    SQLiteStore(db_path)
    assert len(store.get_tasks(date(2026, 10, 31), date(2026, 10, 31))) == 1
