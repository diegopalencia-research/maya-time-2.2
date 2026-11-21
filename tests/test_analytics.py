from analytics import activity_heatmap, summary_metrics, tasks_to_frame, time_by_category


def sample_tasks():
    return [
        {
            "id": 1, "event_date": "2026-11-02", "start_time": "08:30", "end_time": "10:00",
            "title": "Research", "category": "Research", "priority": 1,
            "deadline": None, "completed": 1, "notes": "",
        },
        {
            "id": 2, "event_date": "2026-11-02", "start_time": "13:00", "end_time": "14:00",
            "title": "Work", "category": "Work", "priority": 2,
            "deadline": None, "completed": 0, "notes": "",
        },
    ]


def test_task_duration_and_summary():
    frame = tasks_to_frame(sample_tasks())
    summary = summary_metrics(frame)
    assert frame["minutes"].tolist() == [90.0, 60.0]
    assert summary["tasks"] == 2
    assert summary["planned_hours"] == 2.5
    assert summary["completed"] == 1
    assert summary["completion_rate"] == 50.0


def test_category_totals():
    frame = tasks_to_frame(sample_tasks())
    totals = time_by_category(frame).set_index("category")["hours"]
    assert totals["Research"] == 1.5
    assert totals["Work"] == 1.0


def test_heatmap_splits_time_across_hour_cells():
    frame = tasks_to_frame(sample_tasks())
    heat = activity_heatmap(frame)
    assert heat.loc["Mon", 8] == 30.0
    assert heat.loc["Mon", 9] == 60.0
    assert heat.loc["Mon", 13] == 60.0


def test_heatmap_accepts_postgres_time_with_seconds():
    task = [{
        "id": "uuid-1", "event_date": "2026-11-02", "start_time": "08:30:00",
        "end_time": "09:30:00", "title": "Research", "category": "Research",
        "priority": 1, "deadline": None, "completed": False, "notes": "",
    }]
    heat = activity_heatmap(tasks_to_frame(task))
    assert heat.loc["Mon", 8] == 30.0
    assert heat.loc["Mon", 9] == 30.0
