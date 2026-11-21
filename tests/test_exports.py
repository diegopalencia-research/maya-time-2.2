from datetime import date
from io import BytesIO

from openpyxl import load_workbook

from exports import build_excel_workbook


def test_excel_export_has_expected_sheets_and_records():
    tasks = [{
        "id": 1, "series_id": "series-1", "event_date": "2026-11-01",
        "start_time": "08:00", "end_time": "09:00", "title": "Research",
        "category": "Research", "priority": 1, "deadline": None,
        "completed": 1, "notes": "test", "frequency": "once", "weekdays": [0, 2], "user_id": "private-id",
    }]
    series = [{"id": "series-1", "title": "Research", "category": "Research",
              "priority": 1, "start_date": "2026-11-01", "frequency": "once",
              "repeat_until": "2026-11-01", "deadline": None, "notes": "test", "weekdays": [0, 2], "user_id": "private-id"}]
    reflections = [{"entry_date": "2026-11-01", "mood": "Focused", "energy": 4, "note": "test"}]
    payload = build_excel_workbook(tasks, series, reflections)
    workbook = load_workbook(BytesIO(payload), read_only=True)
    assert workbook.sheetnames == ["Occurrences", "Activity series", "Deadlines", "Reflections", "Time by category", "Time by weekday"]
    assert workbook["Occurrences"]["A2"].value == 1
    assert "private-id" not in [cell.value for row in workbook["Occurrences"].iter_rows() for cell in row]
