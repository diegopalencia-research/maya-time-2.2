from datetime import date

import pytest

pytest.importorskip("astronomy")

from astronomy_layer import calculate_sky_positions  # noqa: E402


def test_astronomy_output_structure_and_ranges():
    result = calculate_sky_positions(date(2026, 11, 1))
    assert result["timestamp_local"].startswith("2026-11-01T12:00:00")
    assert 0 <= result["moon_phase_angle"] < 360
    assert 0 <= result["moon_illumination"] <= 1
    bodies = {row["body"] for row in result["positions"]}
    assert bodies == {
        "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
        "Saturn", "Uranus", "Neptune", "Pluto",
    }
    for row in result["positions"]:
        assert 0 <= row["longitude"] < 360
        assert row["sign"]
        assert 0 <= row["degree_in_sign"] < 30

    heliocentric = result["heliocentric_positions"]
    assert {row["body"] for row in heliocentric} == {
        "Sun", "Mercury", "Venus", "Earth", "Mars", "Jupiter",
        "Saturn", "Uranus", "Neptune", "Pluto",
    }
    for row in heliocentric:
        assert all(isinstance(row[key], float) for key in ("x_au", "y_au", "z_au", "distance_au"))
        assert row["distance_au"] >= 0

    assert len(result["lunar_cycle"]["timestamps"]) == 241
    assert len(result["lunar_cycle"]["illumination"]) == 241
    assert all(0 <= value <= 1 for value in result["lunar_cycle"]["illumination"])
    assert all(0 <= row["orb"] <= 6 for row in result["aspects"])
