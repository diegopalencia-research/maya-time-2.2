"""Deterministic Gregorian ↔ K'iche' Cholq'ij / Classic Maya date conversion.

The default alignment uses GMT correlation 584283. See docs/METHODOLOGY.md
for the anchor, equations, known alternatives, and scope boundaries.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

GMT_CORRELATION = 584_283
DATA_FILE = Path(__file__).parent / "data" / "kiche_day_signs.csv"

HAAB_MONTHS = (
    "Pop", "Wo", "Sip", "Sotz'", "Sek", "Xul", "Yaxk'in", "Mol", "Ch'en",
    "Yax", "Sak", "Keh", "Mak", "K'ank'in", "Muwan", "Pax", "K'ayab",
    "Kumk'u", "Wayeb",
)


@dataclass(frozen=True)
class CalendarDate:
    gregorian: date
    julian_day_number: int
    days_from_epoch: int
    cholqij_number: int
    cholqij_name: str
    cholqij_position: int  # 1..260, within the 260-day cycle
    haab_day: int
    haab_month: str
    long_count: str
    calendar_round_position: int  # 1..18,980

    @property
    def cholqij(self) -> str:
        return f"{self.cholqij_number} {self.cholqij_name}"

    @property
    def haab(self) -> str:
        return f"{self.haab_day} {self.haab_month}"


def load_kiche_day_names() -> tuple[str, ...]:
    """Load the 20 K'iche' day names in the sequence used by the GMT mapping."""
    with DATA_FILE.open("r", encoding="utf-8", newline="") as handle:
        rows = sorted(csv.DictReader(handle), key=lambda row: int(row["sequence_index"]))
    names = tuple(row["kiche_name"] for row in rows)
    if len(names) != 20 or len(set(names)) != 20:
        raise ValueError("The K'iche' day-name reference must contain 20 unique names.")
    return names


KICHE_DAY_NAMES = load_kiche_day_names()


def gregorian_to_jdn(value: date) -> int:
    """Return the integer Julian Day Number for Gregorian midnight."""
    if not isinstance(value, date):
        raise TypeError("value must be datetime.date")
    # Python ordinal 1 = 1 Jan 0001; this offset returns the JDN at midnight.
    return value.toordinal() + 1_721_425


def _long_count(days_from_epoch: int) -> str:
    """Convert elapsed days from LC 0.0.0.0.0 to the five Long Count units."""
    baktun, remainder = divmod(days_from_epoch, 144_000)
    katun, remainder = divmod(remainder, 7_200)
    tun, remainder = divmod(remainder, 360)
    winal, kin = divmod(remainder, 20)
    return f"{baktun}.{katun}.{tun}.{winal}.{kin}"


def convert_date(value: date, correlation: int = GMT_CORRELATION) -> CalendarDate:
    """Convert a Gregorian date using an explicit integer JDN correlation.

    The Cholq'ij number and day-sign cycles follow the documented GMT 584283
    alignment. The K'iche' day-name sequence is used rather than Yucatec names.
    """
    jdn = gregorian_to_jdn(value)
    days = jdn - int(correlation)

    # GMT anchor: 2012-12-21 = 13.0.0.0.0 = 4 Ajaw / 4 Ajpu.
    # 1..13 coefficients advance daily; the 20 names advance independently.
    number = ((days + 3) % 13) + 1
    sign_index = (days + 19) % 20
    sign = KICHE_DAY_NAMES[sign_index]
    cycle_position = (days % 260) + 1

    # Classic Haab' formula under the same GMT alignment.
    haab_position = (days + 348) % 365
    month_index, haab_day = divmod(haab_position, 20)
    haab_month = HAAB_MONTHS[month_index]

    # The Calendar Round repeats every lcm(260, 365) = 18,980 days.
    round_position = (days % 18_980) + 1

    return CalendarDate(
        gregorian=value,
        julian_day_number=jdn,
        days_from_epoch=days,
        cholqij_number=number,
        cholqij_name=sign,
        cholqij_position=cycle_position,
        haab_day=haab_day,
        haab_month=haab_month,
        long_count=_long_count(days),
        calendar_round_position=round_position,
    )


def days_until_day_sign(
    value: date,
    sign_name: str,
    number: Optional[int] = None,
    include_today: bool = True,
) -> int:
    """Return days until the next requested Cholq'ij name/number combination."""
    target = sign_name.casefold().strip()
    for offset in range(0 if include_today else 1, 261):
        result = convert_date(value + timedelta(days=offset))
        if result.cholqij_name.casefold() == target:
            if number is None or result.cholqij_number == number:
                return offset
    raise ValueError(f"Unknown K'iche' day name: {sign_name}")


def next_day_sign_date(
    value: date,
    sign_name: str,
    number: Optional[int] = None,
    include_today: bool = True,
) -> date:
    return value + timedelta(
        days=days_until_day_sign(value, sign_name, number, include_today)
    )
