"""Per-user persistence adapters: local SQLite or authenticated Supabase.

No process-global user/backend state is used: Streamlit sessions each own a
store instance, preventing cross-session identity leakage.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from planner_logic import occurrence_dates

DB_PATH = Path(__file__).parent / "data" / "maya_time.sqlite3"


class SQLiteStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS activity_series (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 2,
                    start_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    frequency TEXT NOT NULL DEFAULT 'once',
                    weekdays TEXT NOT NULL DEFAULT '[]',
                    repeat_until TEXT NOT NULL,
                    deadline TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS activity_occurrences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id TEXT NOT NULL REFERENCES activity_series(id) ON DELETE CASCADE,
                    event_date TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(series_id, event_date)
                );
                CREATE INDEX IF NOT EXISTS idx_occurrences_date ON activity_occurrences(event_date);
                CREATE INDEX IF NOT EXISTS idx_series_start ON activity_series(start_date);
                CREATE TABLE IF NOT EXISTS reflections (
                    entry_date TEXT PRIMARY KEY,
                    mood TEXT NOT NULL DEFAULT '',
                    energy INTEGER NOT NULL DEFAULT 3,
                    note TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS app_migrations (
                    migration_key TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._migrate_legacy_tasks(connection)

    @staticmethod
    def _migrate_legacy_tasks(connection: sqlite3.Connection) -> None:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone()
        migrated = connection.execute(
            "SELECT 1 FROM app_migrations WHERE migration_key='legacy_tasks_v1'"
        ).fetchone()
        if not exists or migrated:
            return
        rows = connection.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        for row in rows:
            item = dict(row)
            series_id = str(uuid.uuid4())
            event_date = item["event_date"]
            connection.execute(
                """INSERT INTO activity_series
                (id,title,category,priority,start_date,start_time,end_time,frequency,
                 weekdays,repeat_until,deadline,notes)
                VALUES (?,?,?,?,?,?,?,'once','[]',?,?,?)""",
                (series_id, item["title"], item["category"], item.get("priority", 2),
                 event_date, item["start_time"], item["end_time"], event_date,
                 item.get("deadline"), item.get("notes", "")),
            )
            connection.execute(
                "INSERT INTO activity_occurrences(series_id,event_date,completed) VALUES (?,?,?)",
                (series_id, event_date, int(item.get("completed", 0))),
            )
        connection.execute(
            "INSERT INTO app_migrations(migration_key) VALUES ('legacy_tasks_v1')"
        )

    def create_activity(
        self,
        *,
        start_date: date,
        start_time: str,
        end_time: str,
        title: str,
        category: str,
        priority: int = 2,
        deadline: date | None = None,
        notes: str = "",
        frequency: str = "once",
        repeat_until: date | None = None,
        weekdays: list[int] | None = None,
    ) -> int:
        self._validate_activity(start_time, end_time, title, priority)
        repeat_until = repeat_until or start_date
        dates = occurrence_dates(start_date, repeat_until, frequency, weekdays)
        series_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO activity_series
                (id,title,category,priority,start_date,start_time,end_time,frequency,
                 weekdays,repeat_until,deadline,notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (series_id, title.strip(), category, int(priority), start_date.isoformat(),
                 start_time, end_time, frequency, json.dumps(sorted(set(weekdays or []))),
                 repeat_until.isoformat(), deadline.isoformat() if deadline else None,
                 notes.strip()),
            )
            cursor = connection.executemany(
                "INSERT INTO activity_occurrences(series_id,event_date) VALUES (?,?)",
                [(series_id, day.isoformat()) for day in dates],
            )
            first = connection.execute(
                "SELECT id FROM activity_occurrences WHERE series_id=? ORDER BY event_date LIMIT 1",
                (series_id,),
            ).fetchone()
            return int(first["id"])

    @staticmethod
    def _validate_activity(start_time: str, end_time: str, title: str, priority: int) -> None:
        if not title.strip():
            raise ValueError("Activity title cannot be empty.")
        if start_time >= end_time:
            raise ValueError("End time must be later than start time.")
        if priority not in (1, 2, 3):
            raise ValueError("Priority must be 1, 2, or 3.")

    def get_tasks(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT o.id, o.series_id, o.event_date, o.completed,
                          s.title, s.category, s.priority, s.start_time, s.end_time,
                          s.deadline, s.notes, s.frequency, s.start_date AS series_start,
                          s.repeat_until, s.weekdays
                   FROM activity_occurrences o
                   JOIN activity_series s ON s.id=o.series_id
                   WHERE o.event_date BETWEEN ? AND ?
                   ORDER BY o.event_date, s.start_time, o.id""",
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["weekdays"] = json.loads(item["weekdays"] or "[]")
            output.append(item)
        return output

    def get_all_series(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM activity_series ORDER BY start_date").fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["weekdays"] = json.loads(item["weekdays"] or "[]")
            output.append(item)
        return output

    def get_all_tasks(self) -> list[dict[str, Any]]:
        return self.get_tasks(date(1900, 1, 1), date(2200, 12, 31))

    def set_task_completed(self, task_id: int, completed: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE activity_occurrences SET completed=? WHERE id=?",
                (1 if completed else 0, int(task_id)),
            )

    def delete_task(self, task_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM activity_occurrences WHERE id=?", (int(task_id),))

    def delete_series(self, series_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM activity_series WHERE id=?", (series_id,))

    def update_series(self, series_id: str, **values: Any) -> None:
        allowed = {"title", "category", "priority", "start_time", "end_time", "deadline", "notes"}
        update = {key: value for key, value in values.items() if key in allowed}
        if not update:
            return
        if "title" in update and not str(update["title"]).strip():
            raise ValueError("Activity title cannot be empty.")
        if "start_time" in update and "end_time" in update:
            self._validate_activity(update["start_time"], update["end_time"], update.get("title", "Activity"), int(update.get("priority", 2)))
        assignments = ",".join(f"{key}=?" for key in update)
        params = [update[key] for key in update] + [series_id]
        with self._connect() as connection:
            connection.execute(f"UPDATE activity_series SET {assignments} WHERE id=?", params)

    def save_reflection(self, entry_date: date, mood: str, energy: int, note: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO reflections(entry_date,mood,energy,note)
                VALUES (?,?,?,?) ON CONFLICT(entry_date) DO UPDATE SET
                mood=excluded.mood, energy=excluded.energy, note=excluded.note,
                updated_at=CURRENT_TIMESTAMP""",
                (entry_date.isoformat(), mood, int(energy), note.strip()),
            )

    def get_reflection(self, entry_date: date) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reflections WHERE entry_date=?", (entry_date.isoformat(),)
            ).fetchone()
        return dict(row) if row else None

    def get_reflections(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reflections WHERE entry_date BETWEEN ? AND ? ORDER BY entry_date",
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_all_reflections(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM reflections ORDER BY entry_date").fetchall()
        return [dict(row) for row in rows]


class SupabaseStore:
    """Supabase Data API adapter. The client must be authenticated as user_id.

    All tables use RLS with auth.uid() = user_id. A publishable/anon key is
    sufficient; never pass a service_role/secret key to this class.
    """
    def __init__(self, client: Any, user_id: str):
        self.client = client
        self.user_id = str(user_id)

    def create_activity(
        self, *, start_date: date, start_time: str, end_time: str, title: str,
        category: str, priority: int = 2, deadline: date | None = None,
        notes: str = "", frequency: str = "once", repeat_until: date | None = None,
        weekdays: list[int] | None = None,
    ) -> str:
        SQLiteStore._validate_activity(start_time, end_time, title, priority)
        repeat_until = repeat_until or start_date
        dates = occurrence_dates(start_date, repeat_until, frequency, weekdays)
        series_payload = {
            "user_id": self.user_id, "title": title.strip(), "category": category,
            "priority": int(priority), "start_date": start_date.isoformat(),
            "start_time": start_time, "end_time": end_time, "frequency": frequency,
            "weekdays": sorted(set(weekdays or [])), "repeat_until": repeat_until.isoformat(),
            "deadline": deadline.isoformat() if deadline else None, "notes": notes.strip(),
        }
        series_result = self.client.table("activity_series").insert(series_payload).execute()
        series = series_result.data[0]
        series_id = series["id"]
        try:
            occurrence_payload = [
                {"user_id": self.user_id, "series_id": series_id, "event_date": day.isoformat()}
                for day in dates
            ]
            self.client.table("activity_occurrences").insert(occurrence_payload).execute()
        except Exception:
            self.client.table("activity_series").delete().eq("id", series_id).eq("user_id", self.user_id).execute()
            raise
        return series_id

    def get_tasks(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        occurrences = self.client.table("activity_occurrences").select("*").eq(
            "user_id", self.user_id
        ).gte("event_date", start_date.isoformat()).lte(
            "event_date", end_date.isoformat()
        ).order("event_date").execute().data or []
        series_ids = sorted({row["series_id"] for row in occurrences})
        if not series_ids:
            return []
        series_rows = self.client.table("activity_series").select("*").eq(
            "user_id", self.user_id
        ).in_("id", series_ids).execute().data or []
        series_map = {row["id"]: row for row in series_rows}
        output = []
        for occurrence in occurrences:
            series = series_map.get(occurrence["series_id"])
            if not series:
                continue
            output.append({**series, **occurrence,
                           "event_date": occurrence["event_date"],
                           "completed": int(bool(occurrence["completed"]))})
        return sorted(output, key=lambda row: (row["event_date"], row["start_time"], str(row["id"])))

    def get_all_tasks(self) -> list[dict[str, Any]]:
        return self.get_tasks(date(1900, 1, 1), date(2200, 12, 31))

    def get_all_series(self) -> list[dict[str, Any]]:
        return self.client.table("activity_series").select("*").eq(
            "user_id", self.user_id
        ).order("start_date").execute().data or []

    def set_task_completed(self, task_id: str | int, completed: bool) -> None:
        self.client.table("activity_occurrences").update({"completed": bool(completed)}).eq(
            "id", task_id
        ).eq("user_id", self.user_id).execute()

    def delete_task(self, task_id: str | int) -> None:
        self.client.table("activity_occurrences").delete().eq(
            "id", task_id
        ).eq("user_id", self.user_id).execute()

    def delete_series(self, series_id: str) -> None:
        self.client.table("activity_series").delete().eq(
            "id", series_id
        ).eq("user_id", self.user_id).execute()

    def update_series(self, series_id: str, **values: Any) -> None:
        allowed = {"title", "category", "priority", "start_time", "end_time", "deadline", "notes"}
        update = {key: value for key, value in values.items() if key in allowed}
        if not update:
            return
        if update.get("title", "Activity").strip() == "":
            raise ValueError("Activity title cannot be empty.")
        if "start_time" in update and "end_time" in update and update["start_time"] >= update["end_time"]:
            raise ValueError("End time must be later than start time.")
        self.client.table("activity_series").update(update).eq(
            "id", series_id
        ).eq("user_id", self.user_id).execute()

    def save_reflection(self, entry_date: date, mood: str, energy: int, note: str) -> None:
        self.client.table("reflections").upsert({
            "user_id": self.user_id, "entry_date": entry_date.isoformat(),
            "mood": mood, "energy": int(energy), "note": note.strip(),
        }, on_conflict="user_id,entry_date").execute()

    def get_reflection(self, entry_date: date) -> dict[str, Any] | None:
        rows = self.client.table("reflections").select("*").eq(
            "user_id", self.user_id
        ).eq("entry_date", entry_date.isoformat()).limit(1).execute().data or []
        return rows[0] if rows else None

    def get_reflections(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return self.client.table("reflections").select("*").eq(
            "user_id", self.user_id
        ).gte("entry_date", start_date.isoformat()).lte(
            "entry_date", end_date.isoformat()
        ).order("entry_date").execute().data or []

    def get_all_reflections(self) -> list[dict[str, Any]]:
        return self.client.table("reflections").select("*").eq(
            "user_id", self.user_id
        ).order("entry_date").execute().data or []

