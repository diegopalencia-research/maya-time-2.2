"""Astronomical position and optional symbolic astrology layer.

Astronomical calculations use the MIT-licensed Astronomy Engine package.
Astrological aspect descriptions are traditional symbolic interpretations and
are deliberately kept separate from the astronomical position calculations.
"""

from __future__ import annotations

from datetime import date, datetime, time as clock_time, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL_ZONE = ZoneInfo("America/Guatemala")
ZODIAC_SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
PLANETS = (
    "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
)
BODIES_WITH_LUMINARIES = ("Sun", "Moon") + PLANETS

ASPECT_DEFINITIONS = (
    ("Conjunction", 0.0, "blend / concentration"),
    ("Sextile", 60.0, "cooperation / opportunity"),
    ("Square", 90.0, "friction / adjustment"),
    ("Trine", 120.0, "ease / flow"),
    ("Opposition", 180.0, "polarity / integration"),
)

SYMBOLIC_THEMES = {
    "Sun": "identity, vitality and purpose",
    "Moon": "needs, habits and emotional life",
    "Mercury": "thinking, learning and communication",
    "Venus": "affection, values and attraction",
    "Mars": "drive, assertion and action",
    "Jupiter": "growth, belief and opportunity",
    "Saturn": "structure, limits and responsibility",
    "Uranus": "change, independence and experimentation",
    "Neptune": "imagination, ideals and ambiguity",
    "Pluto": "power, intensity and transformation",
}

ASPECT_READINGS = {
    "Conjunction": "The two themes are traditionally read as combined or intensified.",
    "Sextile": "The two themes are traditionally read as having room for cooperation or development.",
    "Square": "The two themes are traditionally read as creating friction that calls for adjustment.",
    "Trine": "The two themes are traditionally read as flowing together with relative ease.",
    "Opposition": "The two themes are traditionally read as a polarity to recognize and integrate.",
}

# Mean orbital radii (semi-major-axis approximations) in AU. These are used only
# as circular visual guides; the plotted planetary dots come from ephemeris vectors.
MEAN_ORBIT_AU = {
    "Mercury": 0.3871,
    "Venus": 0.7233,
    "Earth": 1.0000,
    "Mars": 1.5237,
    "Jupiter": 5.2028,
    "Saturn": 9.5388,
    "Uranus": 19.1914,
    "Neptune": 30.0611,
    "Pluto": 39.482,
}


def _zodiac_position(longitude: float) -> tuple[str, float]:
    normalized = longitude % 360.0
    sign_index = int(normalized // 30.0)
    return ZODIAC_SIGNS[sign_index], normalized % 30.0


def _signed_delta(a: float, b: float) -> float:
    """Smallest signed angular displacement from a to b, in degrees."""
    return (b - a + 180.0) % 360.0 - 180.0


def _utc_time_for_local_noon(selected_date: date):
    local_noon = datetime.combine(selected_date, clock_time(12, 0), tzinfo=LOCAL_ZONE)
    utc = local_noon.astimezone(timezone.utc)
    import astronomy
    return astronomy.Time.Make(utc.year, utc.month, utc.day, utc.hour, utc.minute, float(utc.second))


def calculate_aspects(positions: list[dict], orb_limit: float = 6.0) -> list[dict]:
    """Return major geocentric ecliptic-longitude aspects within ``orb_limit``.

    Angular separation is based on tropical ecliptic longitude, not 3-D distance.
    The interpretation field is a traditional symbolic prompt, not a scientific
    claim about causal effects.
    """
    aspects: list[dict] = []
    for index, first in enumerate(positions):
        for second in positions[index + 1:]:
            separation = abs(_signed_delta(float(first["longitude"]), float(second["longitude"])))
            nearest = min(ASPECT_DEFINITIONS, key=lambda item: abs(separation - item[1]))
            name, exact_angle, theme = nearest
            orb = abs(separation - exact_angle)
            if orb > orb_limit:
                continue
            body_a, body_b = str(first["body"]), str(second["body"])
            aspects.append({
                "body_a": body_a,
                "body_b": body_b,
                "aspect": name,
                "angle": separation,
                "exact_angle": exact_angle,
                "orb": orb,
                "theme": theme,
                "interpretation": (
                    f"{body_a} ({SYMBOLIC_THEMES.get(body_a, 'symbolic theme')}) and "
                    f"{body_b} ({SYMBOLIC_THEMES.get(body_b, 'symbolic theme')}): "
                    f"{ASPECT_READINGS[name]}"
                ),
            })
    return sorted(aspects, key=lambda item: (item["orb"], item["angle"]))


def calculate_heliocentric_positions(selected_date: date) -> list[dict]:
    """Calculate heliocentric XYZ positions in the J2000 mean ecliptic frame.

    Coordinates are in astronomical units (AU), with the Sun at the origin.
    The plotted XY plane is a projection; Z is retained in the records so the
    user can inspect each body's out-of-plane coordinate.
    """
    try:
        import astronomy
    except ImportError as exc:
        raise RuntimeError(
            "Install the astronomy-engine dependency to calculate sky positions."
        ) from exc

    moment = _utc_time_for_local_noon(selected_date)
    eqj_to_ecl = astronomy.Rotation_EQJ_ECL()
    records = [{
        "body": "Sun", "x_au": 0.0, "y_au": 0.0, "z_au": 0.0,
        "distance_au": 0.0,
    }]
    for name in ("Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"):
        vector_eqj = astronomy.HelioVector(getattr(astronomy.Body, name), moment)
        vector_ecl = astronomy.RotateVector(eqj_to_ecl, vector_eqj)
        x, y, z = float(vector_ecl.x), float(vector_ecl.y), float(vector_ecl.z)
        records.append({
            "body": name,
            "x_au": x,
            "y_au": y,
            "z_au": z,
            "distance_au": (x * x + y * y + z * z) ** 0.5,
        })
    return records


def calculate_lunar_cycle(selected_date: date, span_days: int = 15) -> dict:
    """Sample modeled lunar illumination around a selected date.

    The default span returns roughly one synodic month centered on the selected
    date. Samples are calculated every six hours; quarter dates are ephemeris
    events returned by Astronomy Engine.
    """
    try:
        import astronomy
    except ImportError as exc:
        raise RuntimeError(
            "Install the astronomy-engine dependency to calculate sky positions."
        ) from exc

    start_date = selected_date - timedelta(days=span_days)
    end_date = selected_date + timedelta(days=span_days)
    start_time = _utc_time_for_local_noon(start_date)
    end_time = _utc_time_for_local_noon(end_date)

    timestamps: list[str] = []
    illumination: list[float] = []
    samples = int(span_days * 16) + 1  # symmetric window, one sample every three hours
    for index in range(samples):
        moment = start_time.AddDays(index * 0.125)
        local_dt = moment.Utc().replace(tzinfo=timezone.utc).astimezone(LOCAL_ZONE)
        timestamps.append(local_dt.isoformat())
        illumination.append(float(astronomy.Illumination(astronomy.Body.Moon, moment).phase_fraction))

    quarter_names = ("New Moon", "First Quarter", "Full Moon", "Last Quarter")
    quarter_events: list[dict] = []
    try:
        event = astronomy.SearchMoonQuarter(start_time)
        while event is not None and event.time.ut <= end_time.ut:
            utc_dt = event.time.Utc().replace(tzinfo=timezone.utc)
            local_dt = utc_dt.astimezone(LOCAL_ZONE)
            quarter_events.append({
                "phase": quarter_names[int(event.quarter) % 4],
                "timestamp": local_dt.isoformat(),
                "utc_timestamp": utc_dt.isoformat(),
            })
            event = astronomy.NextMoonQuarter(event)
    except Exception:
        # The illumination series remains useful even if an event search fails.
        quarter_events = []

    return {
        "timestamps": timestamps,
        "illumination": illumination,
        "quarter_events": quarter_events,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "sample_interval_hours": 3,
    }


def calculate_sky_positions(selected_date: date) -> dict:
    """Calculate geocentric tropical longitudes and apparent retrograde status.

    The calculation is timestamped at 12:00 America/Guatemala. Retrograde is
    estimated from the signed change in geocentric ecliptic longitude over the
    following 24 hours. It is a kinematic description, not a physical reversal.
    """
    try:
        import astronomy
    except ImportError as exc:
        raise RuntimeError(
            "Install the astronomy-engine dependency to calculate sky positions."
        ) from exc

    moment = _utc_time_for_local_noon(selected_date)
    next_moment = moment.AddDays(1.0)

    def longitude(body_name: str, at_time) -> float:
        if body_name == "Sun":
            return float(astronomy.SunPosition(at_time).elon) % 360.0
        if body_name == "Moon":
            return float(astronomy.EclipticGeoMoon(at_time).lon) % 360.0
        body = getattr(astronomy.Body, body_name)
        vector = astronomy.GeoVector(body, at_time, True)
        return float(astronomy.Ecliptic(vector).elon) % 360.0

    records = []
    for name in BODIES_WITH_LUMINARIES:
        current = longitude(name, moment)
        following = longitude(name, next_moment)
        daily_motion = _signed_delta(current, following)
        sign, degree = _zodiac_position(current)
        records.append({
            "body": name,
            "longitude": current,
            "sign": sign,
            "degree_in_sign": degree,
            "daily_motion": daily_motion,
            "retrograde": name in PLANETS and daily_motion < 0,
        })

    phase_angle = float(astronomy.MoonPhase(moment)) % 360.0
    illumination = float(astronomy.Illumination(astronomy.Body.Moon, moment).phase_fraction)
    phase_labels = (
        "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
        "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
    )
    phase_index = int((phase_angle + 22.5) // 45.0) % 8

    timestamp_local = datetime.combine(
        selected_date, clock_time(12, 0), tzinfo=LOCAL_ZONE
    ).isoformat()

    return {
        "timestamp_local": timestamp_local,
        "positions": records,
        "aspects": calculate_aspects(records),
        "heliocentric_positions": calculate_heliocentric_positions(selected_date),
        "lunar_cycle": calculate_lunar_cycle(selected_date),
        "moon_phase_angle": phase_angle,
        "moon_phase": phase_labels[phase_index],
        "moon_illumination": illumination,
        "zodiac_model": "Tropical · geocentric · date-of-equinox ecliptic",
        "heliocentric_model": "Heliocentric · J2000 mean ecliptic (ECL) · XYZ in AU",
    }
