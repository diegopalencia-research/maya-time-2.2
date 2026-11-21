"""Excel export utilities for Maya Time datasets."""
from __future__ import annotations

from io import BytesIO
import json
from typing import Any

import pandas as pd
from openpyxl.worksheet.table import Table, TableStyleInfo

from analytics import tasks_to_frame, time_by_category, time_by_weekday


def build_excel_workbook(
    tasks: list[dict[str, Any]],
    series: list[dict[str, Any]],
    reflections: list[dict[str, Any]],
) -> bytes:
    """Create a clean multi-sheet .xlsx workbook from the source records."""
    buffer = BytesIO()
    task_frame = pd.DataFrame(tasks).drop(columns=["user_id"], errors="ignore")
    if not task_frame.empty:
        for column in task_frame.columns:
            if task_frame[column].map(lambda value: isinstance(value, (list, dict))).any():
                task_frame[column] = task_frame[column].map(
                    lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                )
    if task_frame.empty:
        task_frame = pd.DataFrame(columns=[
            "id", "series_id", "event_date", "title", "category", "priority",
            "start_time", "end_time", "deadline", "completed", "notes",
        ])
    analysis_frame = tasks_to_frame(tasks)
    category_frame = time_by_category(analysis_frame)
    weekday_frame = time_by_weekday(analysis_frame)
    reflections_frame = pd.DataFrame(reflections).drop(columns=["user_id"], errors="ignore")
    if reflections_frame.empty:
        reflections_frame = pd.DataFrame(columns=["entry_date", "mood", "energy", "note"])
    series_frame = pd.DataFrame(series).drop(columns=["user_id"], errors="ignore")
    if not series_frame.empty:
        for column in series_frame.columns:
            if series_frame[column].map(lambda value: isinstance(value, (list, dict))).any():
                series_frame[column] = series_frame[column].map(
                    lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                )
    if series_frame.empty:
        series_frame = pd.DataFrame(columns=[
            "id", "title", "category", "priority", "start_date", "frequency",
            "repeat_until", "deadline", "notes",
        ])
    deadline_columns = [column for column in ["id", "title", "category", "priority", "start_date", "frequency", "deadline"] if column in series_frame.columns]
    deadlines_frame = series_frame.loc[series_frame["deadline"].notna(), deadline_columns].copy() if "deadline" in series_frame.columns else pd.DataFrame(columns=deadline_columns)
    with pd.ExcelWriter(buffer, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
        task_frame.to_excel(writer, sheet_name="Occurrences", index=False)
        series_frame.to_excel(writer, sheet_name="Activity series", index=False)
        deadlines_frame.to_excel(writer, sheet_name="Deadlines", index=False)
        reflections_frame.to_excel(writer, sheet_name="Reflections", index=False)
        category_frame.to_excel(writer, sheet_name="Time by category", index=False)
        weekday_frame.to_excel(writer, sheet_name="Time by weekday", index=False)
        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.sheet_view.showGridLines = False
            if sheet.max_row >= 2 and sheet.max_column >= 1:
                ref = f"A1:{sheet.cell(sheet.max_row, sheet.max_column).coordinate}"
                safe_name = "T" + "".join(ch for ch in sheet.title if ch.isalnum())[:20]
                table = Table(displayName=safe_name, ref=ref)
                table.tableStyleInfo = TableStyleInfo(
                    name="TableStyleMedium2", showFirstColumn=False,
                    showLastColumn=False, showRowStripes=True, showColumnStripes=False,
                )
                sheet.add_table(table)
            for column_cells in sheet.columns:
                values = [str(cell.value) if cell.value is not None else "" for cell in column_cells[:200]]
                width = min(max(max((len(value) for value in values), default=8) + 2, 10), 42)
                sheet.column_dimensions[column_cells[0].column_letter].width = width
    return buffer.getvalue()
