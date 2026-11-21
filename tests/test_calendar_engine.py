from datetime import date, timedelta

import pytest

from calendar_engine import (
    GMT_CORRELATION,
    KICHE_DAY_NAMES,
    convert_date,
    days_until_day_sign,
    gregorian_to_jdn,
    next_day_sign_date,
)


def test_gmt_anchor_2012_12_21():
    result = convert_date(date(2012, 12, 21))
    assert result.julian_day_number == 2_456_283
    assert result.days_from_epoch == 1_872_000
    assert result.long_count == "13.0.0.0.0"
    assert result.cholqij == "4 Ajpu"
    assert result.haab == "3 K'ank'in"


def test_highland_crosscheck_2020_05_23():
    result = convert_date(date(2020, 5, 23))
    assert result.cholqij == "10 Tz'i'"


def test_cholqij_repeats_after_260_days():
    start = date(2026, 1, 1)
    assert convert_date(start).cholqij == convert_date(start + timedelta(days=260)).cholqij


def test_haab_repeats_after_365_days_under_fixed_cycle():
    start = date(2026, 1, 1)
    assert convert_date(start).haab == convert_date(start + timedelta(days=365)).haab


def test_calendar_round_repeats_after_18980_days():
    start = date(2026, 1, 1)
    later = start + timedelta(days=18_980)
    assert convert_date(start).cholqij == convert_date(later).cholqij
    assert convert_date(start).haab == convert_date(later).haab
    assert convert_date(start).calendar_round_position == convert_date(later).calendar_round_position


def test_day_names_are_twenty_unique_entries():
    assert len(KICHE_DAY_NAMES) == 20
    assert len(set(KICHE_DAY_NAMES)) == 20
    assert KICHE_DAY_NAMES[10] == "B'atz'"


def test_next_8_batz_is_valid_and_within_one_cycle():
    start = date(2026, 11, 1)
    offset = days_until_day_sign(start, "B'atz'", number=8)
    result = convert_date(next_day_sign_date(start, "B'atz'", number=8))
    assert 0 <= offset < 260
    assert result.cholqij == "8 B'atz'"


def test_next_day_sign_rejects_unknown_name():
    with pytest.raises(ValueError):
        days_until_day_sign(date(2026, 1, 1), "Unknown")


def test_jdn_consistency():
    assert gregorian_to_jdn(date(2012, 12, 21)) == GMT_CORRELATION + 1_872_000
