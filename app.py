from __future__ import annotations

import calendar
import os
from typing import Any
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import (
    activity_heatmap,
    demo_tasks,
    summary_metrics,
    tasks_to_frame,
    time_by_category,
    time_by_weekday,
)
from astronomy_layer import MEAN_ORBIT_AU, calculate_sky_positions
from calendar_engine import (
    KICHE_DAY_NAMES,
    convert_date,
    days_until_day_sign,
    next_day_sign_date,
)
from exports import build_excel_workbook
from storage import SQLiteStore, SupabaseStore

LOCAL_ZONE = ZoneInfo("America/Guatemala")
TODAY = datetime.now(LOCAL_ZONE).date()


def setting(name: str, default: str | None = None) -> str | None:
    # Explicit environment variables override Streamlit secrets. This lets the
    # Windows launcher force local SQLite even when Supabase secrets exist.
    value = os.getenv(name)
    if value not in (None, ""):
        return str(value)
    try:
        value = st.secrets.get(name, default)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return str(default) if default not in (None, "") else None


STORAGE_MODE = (setting("MAYA_TIME_STORAGE", "demo") or "demo").strip().lower()
if STORAGE_MODE not in {"local", "demo", "supabase"}:
    STORAGE_MODE = "demo"

st.set_page_config(
    page_title="MAYA TIME",
    page_icon="◌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');
    :root {
      --bg: #0b0e12; --panel: #11161c; --line: #26303a;
      --text: #e8e7e2; --muted: #89939d; --gold: #b6a27a;
    }
    .stApp { background: var(--bg); color: var(--text); }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { letter-spacing: -0.035em; font-weight: 500 !important; }
    h1 { font-size: 2.15rem !important; }
    .eyebrow, .mono, code, [data-testid="stMetricLabel"] {
      font-family: 'DM Mono', monospace !important;
      letter-spacing: .08em; text-transform: uppercase;
    }
    .eyebrow { color: var(--gold); font-size: .68rem; }
    .muted { color: var(--muted); }
    .hero-date { font-family: 'DM Mono', monospace; font-size: clamp(2rem, 5vw, 3.5rem); letter-spacing: -.07em; }
    .hero-nawal { font-family: 'DM Mono', monospace; color: var(--gold); font-size: clamp(1.8rem, 4vw, 3rem); letter-spacing: -.06em; }
    .rule { border-top: 1px solid var(--line); margin: .8rem 0 1.1rem 0; }
    .data-label { color: var(--muted); font-family: 'DM Mono', monospace; font-size: .65rem; letter-spacing: .1em; text-transform: uppercase; }
    .clock-panel { border-bottom: 1px solid var(--line); padding: .15rem 0 .7rem 0; margin-bottom: .65rem; }
    .clock-label { color: var(--gold); font-family: 'DM Mono', monospace; font-size: .62rem; letter-spacing: .12em; text-transform: uppercase; }
    .clock-time { color: var(--text); font-family: 'DM Mono', monospace; font-size: clamp(1.2rem, 2.5vw, 1.8rem); letter-spacing: -.055em; line-height: 1.35; font-variant-numeric: tabular-nums; }
    .clock-note { color: var(--muted); font-family: 'DM Mono', monospace; font-size: .6rem; letter-spacing: .06em; }
    div[data-testid="stMetric"] { background: transparent; border: 0; padding: .2rem 0; }
    div[data-testid="stMetricValue"] { font-family: 'DM Mono', monospace; font-size: 1.55rem; }
    div[data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stSidebar"] { background: #090c10; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] * { font-size: .9rem; }
    .stButton button, .stDownloadButton button { border-radius: 3px; border: 1px solid var(--line); }
    .stButton button[kind="primary"] { background: var(--gold); color: #11161c; border: 0; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); }
    div[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 4px; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.fragment(run_every="1s")
def render_mission_clock() -> None:
    local_now = datetime.now(LOCAL_ZONE)
    utc_now = datetime.now(timezone.utc)
    left, right, spacer = st.columns([1, 1, 2])
    with left:
        st.markdown(
            f"<div class='clock-panel'><div class='clock-label'>LOCAL / GUATEMALA</div>"
            f"<div class='clock-time'>{local_now:%H:%M:%S}</div>"
            f"<div class='clock-note'>UTC−06:00 · 24H</div></div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"<div class='clock-panel'><div class='clock-label'>UTC / ISS OPERATIONS / ZULU</div>"
            f"<div class='clock-time'>{utc_now:%H:%M:%S}</div>"
            f"<div class='clock-note'>UTC+00:00 · ISS USES UTC</div></div>",
            unsafe_allow_html=True,
        )
    with spacer:
        st.markdown(
            f"<div class='clock-panel' style='text-align:right'><div class='clock-label'>SYSTEM DATE</div>"
            f"<div class='clock-time' style='font-size:1.05rem'>{local_now:%d %b %Y}</div>"
            f"<div class='clock-note'>AMERICA/GUATEMALA</div></div>",
            unsafe_allow_html=True,
        )


def render_date_navigation() -> date:
    if "focus_date" not in st.session_state:
        st.session_state.focus_date = TODAY
    st.markdown('<div class="data-label">DATE NAVIGATION / SELECTED CIVIL DATE</div>', unsafe_allow_html=True)
    prev_col, date_col, next_col, today_col = st.columns([0.12, 0.50, 0.12, 0.18])
    with prev_col:
        if st.button("←", key="date_previous", help="Previous day", use_container_width=True):
            st.session_state.focus_date -= timedelta(days=1)
            st.rerun()
    with date_col:
        st.date_input("FOCUS DATE", key="focus_date", label_visibility="collapsed")
    with next_col:
        if st.button("→", key="date_next", help="Next day", use_container_width=True):
            st.session_state.focus_date += timedelta(days=1)
            st.rerun()
    with today_col:
        if st.button("◉ TODAY", key="date_today", use_container_width=True):
            st.session_state.focus_date = TODAY
            st.rerun()
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    return st.session_state.focus_date


@st.cache_data(show_spinner=False)
def sky_data_for_date(selected: date) -> dict:
    """Cache the multi-chart ephemeris bundle for each selected civil date."""
    return calculate_sky_positions(selected)


def plot_theme(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=24, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono, monospace", color="#89939d", size=10),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#26303a", tickfont_size=9)
    fig.update_yaxes(showgrid=True, gridcolor="#202831", zeroline=False, linecolor="#26303a", tickfont_size=9)
    return fig


def cycle_figure(number: int, sign_name: str) -> go.Figure:
    sign_index = KICHE_DAY_NAMES.index(sign_name)
    theta, radius, colors, hover = [], [], [], []
    for n in range(1, 14):
        for idx, name in enumerate(KICHE_DAY_NAMES):
            theta.append(idx * 18)
            radius.append(n)
            active = n == number and idx == sign_index
            colors.append("#d6c49b" if active else "#34414d")
            hover.append(f"{n} {name}" + (" · selected" if active else ""))
    fig = go.Figure(go.Scatterpolar(
        r=radius, theta=theta, mode="markers",
        marker=dict(size=7, color=colors, line=dict(width=0)),
        text=hover, hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 14], showticklabels=False, ticks="", showline=False, gridcolor="#26303a"),
        angularaxis=dict(showticklabels=False, ticks="", showline=False, gridcolor="#26303a", rotation=90, direction="clockwise"),
    ))
    return plot_theme(fig, 310)


def show_calendar_overview(selected: date) -> None:
    maya = convert_date(selected)
    st.markdown('<div class="eyebrow">CIVIL TIME / CHOLQ\'IJ / GMT MODEL</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-date">{selected.strftime("%d %B %Y").upper()}</div>', unsafe_allow_html=True)
    st.caption(f"{selected.strftime('%A')} · {selected.timetuple().tm_yday:03d} / {366 if calendar.isleap(selected.year) else 365} · AMERICA/GUATEMALA")
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown('<div class="data-label">CHOLQ\'IJ / K\'ICHE\'</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="hero-nawal">{maya.cholqij}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="muted">Cycle position {maya.cholqij_position:03d} / 260</div>', unsafe_allow_html=True)
        st.write("")
        c1, c2 = st.columns(2)
        c1.metric("HAAB' · GMT MODEL", maya.haab)
        c2.metric("LONG COUNT", maya.long_count)
        c3, c4 = st.columns(2)
        c3.metric("JULIAN DAY", f"{maya.julian_day_number:,}")
        c4.metric("CALENDAR ROUND", f"{maya.calendar_round_position:,} / 18,980")
    with right:
        st.markdown('<div class="data-label">260-DAY STRUCTURE / 13 × 20</div>', unsafe_allow_html=True)
        st.plotly_chart(cycle_figure(maya.cholqij_number, maya.cholqij_name), use_container_width=True, config={"displayModeBar": False})

    days_to_batz = days_until_day_sign(selected, "B'atz'")
    days_to_wajxaqib = days_until_day_sign(selected, "B'atz'", number=8)
    next_batz = next_day_sign_date(selected, "B'atz'")
    next_wajxaqib = next_day_sign_date(selected, "B'atz'", number=8)
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">CYCLE MARKERS</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    a.metric("NEXT B'ATZ' DAY", next_batz.strftime("%d %b %Y"), f"{days_to_batz} day(s)")
    b.metric("NEXT WAJXAQIB' B'ATZ'", next_wajxaqib.strftime("%d %b %Y"), f"{days_to_wajxaqib} day(s)")
    if maya.cholqij_name == "B'atz'":
        st.info("Personal reflection · What would you like to begin, connect, or bring into continuity? This prompt is editorial, not a canonical interpretation.")


def zodiac_wheel_figure(positions: list[dict], aspects: list[dict]) -> go.Figure:
    """Geocentric tropical zodiac wheel with planetary points and aspect chords."""
    fig = go.Figure()
    aspect_colors = {
        "Conjunction": "#b6a27a",
        "Sextile": "#829aab",
        "Square": "#b77e72",
        "Trine": "#91a58d",
        "Opposition": "#a78eae",
    }
    position_by_body = {row["body"]: float(row["longitude"]) for row in positions}

    # Twelve sign boundaries and faint inner ring.
    for boundary in range(0, 360, 30):
        fig.add_trace(go.Scatterpolar(
            r=[0.22, 1.0], theta=[boundary, boundary], mode="lines",
            line=dict(color="#34414d", width=1), hoverinfo="skip",
            showlegend=False,
        ))

    # Keep the wheel readable: draw the closest 14 aspects, while the full list
    # remains available in the interpretation table beside the chart.
    for aspect in aspects[:14]:
        a = position_by_body.get(aspect["body_a"])
        b = position_by_body.get(aspect["body_b"])
        if a is None or b is None:
            continue
        fig.add_trace(go.Scatterpolar(
            r=[0.48, 0.48], theta=[a, b], mode="lines",
            line=dict(color=aspect_colors.get(aspect["aspect"], "#65717d"), width=1.15),
            opacity=0.72,
            hovertemplate=(
                f"{aspect['body_a']} {aspect['aspect']} {aspect['body_b']}"
                f"<br>{aspect['angle']:.1f}° · orb {aspect['orb']:.1f}°<extra></extra>"
            ),
            showlegend=False,
        ))

    body_abbr = {
        "Sun": "Su", "Moon": "Mo", "Mercury": "Me", "Venus": "Ve",
        "Mars": "Ma", "Jupiter": "Ju", "Saturn": "Sa", "Uranus": "Ur",
        "Neptune": "Ne", "Pluto": "Pl",
    }
    # Small radial offsets prevent several nearby labels from sitting on top
    # of one another; angular position remains the calculated longitude.
    radii = [0.82, 0.90, 0.78, 0.87, 0.80, 0.92, 0.84, 0.95, 0.76, 0.89]
    fig.add_trace(go.Scatterpolar(
        r=[radii[i % len(radii)] for i in range(len(positions))],
        theta=[float(row["longitude"]) for row in positions],
        mode="markers+text",
        marker=dict(size=8, color="#d6c49b", line=dict(color="#0b0e12", width=1)),
        text=[body_abbr.get(row["body"], row["body"][:2]) for row in positions],
        textposition="top center",
        textfont=dict(size=10, color="#e8e7e2"),
        customdata=[[row["body"], row["sign"], row["degree_in_sign"], row["longitude"]] for row in positions],
        hovertemplate=(
            "%{customdata[0]}<br>%{customdata[1]} "
            "%{customdata[2]:.2f}°<br>Ecliptic longitude %{customdata[3]:.3f}°<extra></extra>"
        ),
        showlegend=False,
    ))

    zodiac_labels = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO",
                     "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES"]
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 1.08], showticklabels=False, ticks="", showline=False,
                            showgrid=True, gridcolor="#26303a"),
            angularaxis=dict(
                tickmode="array", tickvals=[15 + 30 * i for i in range(12)],
                ticktext=zodiac_labels, tickfont=dict(size=8, color="#89939d"),
                ticks="", showline=False, showgrid=False,
                rotation=90, direction="clockwise",
            ),
        ),
    )
    return plot_theme(fig, 430)


def heliocentric_figure(records: list[dict], scale: str = "FULL SYSTEM") -> go.Figure:
    """XY projection of heliocentric J2000 ecliptic coordinates in AU."""
    import math

    included = records if scale == "FULL SYSTEM" else [
        row for row in records if row["body"] in {"Sun", "Mercury", "Venus", "Earth", "Mars"}
    ]
    included_names = {row["body"] for row in included}
    extent = 42.0 if scale == "FULL SYSTEM" else 1.8
    fig = go.Figure()

    # Circular reference guides use mean semi-major axes, not true osculating
    # orbit curves. Actual instantaneous positions are the plotted ephemeris dots.
    for body, radius in MEAN_ORBIT_AU.items():
        if body not in included_names or radius > extent:
            continue
        angles = [math.radians(i * 3) for i in range(121)]
        fig.add_trace(go.Scatter(
            x=[radius * math.cos(angle) for angle in angles],
            y=[radius * math.sin(angle) for angle in angles],
            mode="lines", line=dict(color="#26303a", width=1, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ))

    planet_rows = [row for row in included if row["body"] != "Sun"]
    fig.add_trace(go.Scatter(
        x=[row["x_au"] for row in planet_rows],
        y=[row["y_au"] for row in planet_rows],
        mode="markers+text",
        marker=dict(size=9, color="#b6a27a", line=dict(color="#e8e7e2", width=0.6)),
        text=[row["body"] for row in planet_rows],
        textposition="top center",
        textfont=dict(size=9, color="#e8e7e2"),
        customdata=[[row["z_au"], row["distance_au"]] for row in planet_rows],
        hovertemplate=(
            "%{text}<br>X %{x:.3f} AU · Y %{y:.3f} AU"
            "<br>Z %{customdata[0]:.3f} AU"
            "<br>Sun distance %{customdata[1]:.3f} AU<extra></extra>"
        ),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers+text",
        marker=dict(size=13, color="#e7c77e", line=dict(color="#fff0c9", width=1)),
        text=["SUN"], textposition="bottom center",
        textfont=dict(size=9, color="#e7c77e"),
        hovertemplate="Sun · heliocentric origin (0, 0, 0)<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        xaxis=dict(title="X · AU", range=[-extent, extent], zeroline=True,
                   zerolinecolor="#52606d"),
        yaxis=dict(title="Y · AU", range=[-extent, extent], zeroline=True,
                   zerolinecolor="#52606d", scaleanchor="x", scaleratio=1),
    )
    return plot_theme(fig, 510 if scale == "FULL SYSTEM" else 440)


def lunar_cycle_figure(cycle: dict) -> go.Figure:
    timestamps = [datetime.fromisoformat(value) for value in cycle["timestamps"]]
    values = [float(value) * 100.0 for value in cycle["illumination"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, y=values, mode="lines",
        line=dict(color="#b6a27a", width=2.2),
        fill="tozeroy", fillcolor="rgba(182,162,122,0.08)",
        name="Illumination",
        hovertemplate="%{x|%d %b %Y · %H:%M}<br>%{y:.1f}% illuminated<extra></extra>",
    ))

    marker_x, marker_y, marker_text = [], [], []
    for event in cycle.get("quarter_events", []):
        event_dt = datetime.fromisoformat(event["timestamp"])
        nearest_index = min(range(len(timestamps)), key=lambda i: abs((timestamps[i] - event_dt).total_seconds()))
        marker_x.append(event_dt)
        marker_y.append(values[nearest_index])
        marker_text.append(event["phase"])
    if marker_x:
        for event_dt in marker_x:
            fig.add_shape(
                type="line", x0=event_dt, x1=event_dt, y0=0, y1=100,
                line=dict(color="#52606d", width=1, dash="dot"),
                layer="below",
            )
        fig.add_trace(go.Scatter(
            x=marker_x, y=marker_y, mode="markers+text",
            marker=dict(size=7, color="#e8e7e2", line=dict(color="#b6a27a", width=1)),
            text=marker_text, textposition="top center",
            textfont=dict(size=8, color="#c2c9cf"),
            hovertemplate="%{text}<br>%{x|%d %b %Y · %H:%M}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        xaxis=dict(title="DATE · GUATEMALA TIME", type="date", tickformat="%d %b"),
        yaxis=dict(title="ILLUMINATED DISC · %", range=[0, 100], ticksuffix="%"),
    )
    return plot_theme(fig, 300)


def show_sky(selected: date) -> None:
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">SKY OBSERVATORY / EPHEMERIS + SYMBOLIC LAYER</div>', unsafe_allow_html=True)
    st.caption(f"Selected date: {selected:%d %B %Y} · Model timestamp: 12:00 America/Guatemala")
    try:
        sky = sky_data_for_date(selected)
    except Exception as exc:
        st.warning(f"Sky calculations are unavailable: {exc}")
        return

    metric_cols = st.columns(3)
    metric_cols[0].metric("MOON PHASE", sky["moon_phase"])
    metric_cols[1].metric("ILLUMINATED", f"{sky['moon_illumination'] * 100:.1f}%")
    metric_cols[2].metric("PLANETARY ASPECTS", len(sky["aspects"]), "within 6° orb")

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="data-label">01 / GEOCENTRIC · TROPICAL ZODIAC</div>', unsafe_allow_html=True)
    zodiac_col, aspect_col = st.columns([1.2, 1])
    with zodiac_col:
        st.plotly_chart(
            zodiac_wheel_figure(sky["positions"], sky["aspects"]),
            use_container_width=True, config={"displayModeBar": False},
        )
        st.caption("Earth-centered apparent ecliptic longitude · 12 equal 30° tropical sectors. Planet dots show longitude; aspect chords are color-coded for conjunction, sextile, square, trine and opposition.")
    with aspect_col:
        st.markdown('<div class="data-label">CURRENT ASPECTS / TRADITIONAL SYMBOLISM</div>', unsafe_allow_html=True)
        if sky["aspects"]:
            for aspect in sky["aspects"][:12]:
                st.markdown(
                    f"**{aspect['body_a']} {aspect['aspect'].upper()} {aspect['body_b']}**"
                    f"  \n<small class='muted'>{aspect['angle']:.1f}° separation · "
                    f"{aspect['orb']:.1f}° orb · {aspect['theme']}</small>",
                    unsafe_allow_html=True,
                )
                st.caption(aspect["interpretation"])
        else:
            st.caption("No major aspect falls within the 6° orb threshold for this date.")
        st.caption("Interpretations are traditional astrological symbolism only. They are not evidence of planetary effects on behavior, mood or events.")

    with st.expander("GEOCENTRIC POSITION TABLE / LONGITUDE + MOTION"):
        table = pd.DataFrame(sky["positions"])
        table["ecliptic longitude"] = table["longitude"].map(lambda value: f"{value:07.3f}°")
        table["position in sign"] = table.apply(
            lambda row: f"{row['degree_in_sign']:05.2f}° {row['sign']}", axis=1
        )
        table["motion"] = table.apply(
            lambda row: ("R" if row["retrograde"] else "D") + f"  {row['daily_motion']:+.3f}°/d"
            if row["body"] not in {"Sun", "Moon"} else f"{row['daily_motion']:+.3f}°/d",
            axis=1,
        )
        st.dataframe(
            table[["body", "position in sign", "ecliptic longitude", "motion"]],
            hide_index=True, use_container_width=True,
        )

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="data-label">02 / HELIOCENTRIC · J2000 MEAN ECLIPTIC</div>', unsafe_allow_html=True)
    st.caption("Sun-centered Cartesian positions · J2000 mean ecliptic frame · X/Y projection in AU; Z retained in hover data.")
    scale = st.radio(
        "SPATIAL MAP SCALE", ["FULL SYSTEM", "INNER SYSTEM"], horizontal=True,
        key="solar_map_scale", label_visibility="collapsed",
    )
    st.plotly_chart(
        heliocentric_figure(sky["heliocentric_positions"], scale),
        use_container_width=True, config={"displayModeBar": False},
    )
    st.caption("Planet markers are ephemeris-derived. Dotted circles are mean orbital-radius guides, not calculated orbital paths. Distances and coordinates are not drawn to planetary body size.")

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="data-label">03 / LUNAR CYCLE · MODELED ILLUMINATION</div>', unsafe_allow_html=True)
    st.plotly_chart(
        lunar_cycle_figure(sky["lunar_cycle"]),
        use_container_width=True, config={"displayModeBar": False},
    )
    st.caption("Modeled illuminated fraction sampled every three hours across a 30-day window centered on the selected date. Vertical phase markers identify calculated New Moon, First Quarter, Full Moon and Last Quarter events.")
    st.caption("Source: Astronomy Engine · all calculations are model outputs, not direct telescope observations or spacecraft-navigation data.")


def show_reflection(store: SQLiteStore | SupabaseStore | None, selected: date) -> None:
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">DAILY LOG / PERSONAL OBSERVATION</div>', unsafe_allow_html=True)
    if store is None:
        st.caption("Reflection storage is disabled in the public demo. Sign in with your private storage account or run locally to keep journal entries.")
        return
    previous = store.get_reflection(selected) or {}
    with st.form("daily_reflection"):
        mood_options = ["", "Focused", "Calm", "Restless", "Low energy", "Overloaded", "Positive", "Unclear"]
        mood = st.selectbox("Mood / self-description", mood_options,
            index=mood_options.index(previous.get("mood", "")) if previous.get("mood", "") in mood_options else 0)
        energy = st.slider("Perceived energy", 1, 5, int(previous.get("energy", 3)))
        note = st.text_area("Observation / intention", value=previous.get("note", ""), height=90)
        submitted = st.form_submit_button("SAVE DAILY LOG", type="primary")
    if submitted:
        store.save_reflection(selected, mood, energy, note)
        st.success("Daily observation saved.")


def show_overview(store: SQLiteStore | SupabaseStore | None, selected: date) -> None:
    show_calendar_overview(selected)
    show_sky(selected)
    show_reflection(store, selected)


def _period_bounds(selected: date, period: str) -> tuple[date, date]:
    if period == "WEEK":
        first = selected - timedelta(days=selected.weekday())
        return first, first + timedelta(days=6)
    first = selected.replace(day=1)
    last = selected.replace(day=calendar.monthrange(selected.year, selected.month)[1])
    return first, last


def _download_exports(store: SQLiteStore | SupabaseStore, tasks: list[dict], start: date, end: date, prefix: str) -> None:
    if not tasks:
        st.caption("No records in this range to export.")
        return
    series_ids = {str(row["series_id"]) for row in tasks}
    series = [row for row in store.get_all_series() if str(row["id"]) in series_ids]
    reflections = store.get_reflections(start, end)
    workbook = build_excel_workbook(tasks, series, reflections)
    st.download_button(
        "EXPORT EXCEL WORKBOOK (.XLSX)", data=workbook,
        file_name=f"maya-time-{prefix}-{start.isoformat()}-{end.isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"xlsx-{prefix}-{start.isoformat()}-{end.isoformat()}",
    )
    st.download_button(
        "EXPORT OCCURRENCES (.CSV)", data=pd.DataFrame(tasks).to_csv(index=False).encode("utf-8"),
        file_name=f"maya-time-{prefix}-{start.isoformat()}-{end.isoformat()}.csv",
        mime="text/csv", key=f"csv-{prefix}-{start.isoformat()}-{end.isoformat()}",
    )


def show_planner(store: SQLiteStore | SupabaseStore | None, selected: date) -> None:
    st.markdown('<div class="eyebrow">PERSONAL OPERATIONS / SCHEDULE</div>', unsafe_allow_html=True)
    st.title("Weekly operations.")
    period = st.radio("VIEW", ["WEEK", "MONTH"], horizontal=True, label_visibility="collapsed")
    first, last = _period_bounds(selected, period)
    st.caption(f"{first:%d %b %Y} — {last:%d %b %Y} · {period} VIEW")

    if store is not None:
        with st.expander("+ ADD ACTIVITY / DEFINE RECURRENCE", expanded=True):
            frequency = st.selectbox(
                "REPEAT", ["once", "daily", "weekly", "monthly"],
                format_func=lambda value: {"once": "ONCE · selected date only", "daily": "DAILY", "weekly": "WEEKLY · selected weekdays", "monthly": "MONTHLY · same day of month"}[value],
                key="new_activity_frequency",
            )
            with st.form("create_activity"):
                title = st.text_input("ACTIVITY", placeholder="e.g. Research protocol review")
                c1, c2, c3 = st.columns(3)
                with c1:
                    start_date = st.date_input("START DATE", value=selected)
                with c2:
                    start_time = st.time_input("START", value=time(8, 0), step=timedelta(minutes=15))
                with c3:
                    end_time = st.time_input("END", value=time(9, 0), step=timedelta(minutes=15))
                repeat_until = start_date
                weekdays: list[int] = []
                if frequency != "once":
                    default_horizon = 365 if frequency == "monthly" else 30
                    repeat_until = st.date_input("REPEAT THROUGH (INCLUSIVE)", value=start_date + timedelta(days=default_horizon), min_value=start_date)
                if frequency == "weekly":
                    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    weekdays = st.multiselect("WEEKDAYS", names, default=[names[start_date.weekday()]])
                d1, d2, d3 = st.columns(3)
                with d1:
                    category = st.selectbox("CATEGORY", ["Work", "Research", "Development", "Writing", "Learning", "Training", "Rest", "Personal", "Planning", "Other"])
                with d2:
                    priority = st.selectbox("PRIORITY", [1, 2, 3], index=1, format_func=lambda n: {1: "01 · HIGH", 2: "02 · NORMAL", 3: "03 · LOW"}[n])
                with d3:
                    attach_deadline = st.checkbox("ATTACH DEADLINE")
                    deadline = st.date_input("DEADLINE", value=start_date) if attach_deadline else None
                notes = st.text_input("NOTES (OPTIONAL)")
                submitted = st.form_submit_button("SAVE ACTIVITY / GENERATE OCCURRENCES", type="primary")
            if submitted:
                if frequency == "weekly" and not weekdays:
                    st.error("Select at least one weekday for a weekly recurrence.")
                elif start_time >= end_time:
                    st.error("End time must be later than start time.")
                elif not title.strip():
                    st.error("Enter an activity name.")
                else:
                    weekday_numbers = [ ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(name) for name in weekdays ]
                    try:
                        store.create_activity(
                            start_date=start_date, start_time=start_time.strftime("%H:%M"),
                            end_time=end_time.strftime("%H:%M"), title=title,
                            category=category, priority=priority, deadline=deadline,
                            notes=notes, frequency=frequency, repeat_until=repeat_until,
                            weekdays=weekday_numbers,
                        )
                        st.success("Activity saved. Scheduled dates were generated as separate occurrences.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save activity: {exc}")
    else:
        st.info("PUBLIC DEMO · The schedule uses synthetic demonstration records. Sign in with Supabase or run locally to create and store private activities.")

    tasks = store.get_tasks(first, last) if store is not None else [
        row for row in demo_tasks(first, last)
        if first <= date.fromisoformat(row["event_date"]) <= last
    ]
    frame = tasks_to_frame(tasks)
    metrics = summary_metrics(frame)
    m1, m2, m3 = st.columns(3)
    m1.metric("OCCURRENCES", metrics["tasks"])
    m2.metric("SCHEDULED", f"{metrics['planned_hours']:.1f} h")
    m3.metric("COMPLETED", f"{metrics['completion_rate']:.0f}%")
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    if not tasks:
        st.caption("No activities in this period. Add the first one above.")
    else:
        seen_series: set[str] = set()
        for task in tasks:
            row1, row2, row3, row4 = st.columns([0.07, 0.53, 0.25, 0.15])
            if store is not None:
                checked = row1.checkbox("Done", value=bool(task["completed"]), key=f"complete-{task['id']}-{task['completed']}", label_visibility="collapsed")
                if checked != bool(task["completed"]):
                    store.set_task_completed(task["id"], checked)
                    st.rerun()
            else:
                row1.write("✓" if task["completed"] else "·")
            row2.markdown(
                f"**{task['title']}**  \n<small class='muted'>{task['category']} · P{task['priority']} · {str(task.get('frequency','once')).upper()}</small>",
                unsafe_allow_html=True,
            )
            row3.caption(f"{task['event_date']}  {task['start_time']}–{task['end_time']}")
            if store is not None:
                if row4.button("DELETE", key=f"delete-occurrence-{task['id']}"):
                    store.delete_task(task["id"])
                    st.rerun()
            elif task.get("deadline"):
                row4.caption(f"DUE {task['deadline']}")
            st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

            series_id = str(task.get("series_id", task.get("id")))
            if store is not None and series_id not in seen_series:
                seen_series.add(series_id)
                with st.expander(f"EDIT SERIES · {task['title']} · {series_id[:8]}"):
                    with st.form(f"edit-series-{series_id}"):
                        e_title = st.text_input("ACTIVITY", value=task["title"], key=f"edit-title-{series_id}")
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            e_start = st.time_input("START", value=time.fromisoformat(task["start_time"]), key=f"edit-start-{series_id}")
                        with ec2:
                            e_end = st.time_input("END", value=time.fromisoformat(task["end_time"]), key=f"edit-end-{series_id}")
                        with ec3:
                            e_priority = st.selectbox("PRIORITY", [1, 2, 3], index=max(0, min(2, int(task["priority"]) - 1)), key=f"edit-priority-{series_id}")
                        e_category = st.selectbox("CATEGORY", ["Work", "Research", "Development", "Writing", "Learning", "Training", "Rest", "Personal", "Planning", "Other"], index=["Work", "Research", "Development", "Writing", "Learning", "Training", "Rest", "Personal", "Planning", "Other"].index(task["category"]) if task["category"] in ["Work", "Research", "Development", "Writing", "Learning", "Training", "Rest", "Personal", "Planning", "Other"] else 9, key=f"edit-category-{series_id}")
                        e_deadline_on = st.checkbox("ATTACH DEADLINE", value=bool(task.get("deadline")), key=f"edit-deadline-on-{series_id}")
                        e_deadline = st.date_input("DEADLINE", value=date.fromisoformat(task["deadline"]) if task.get("deadline") else selected, key=f"edit-deadline-{series_id}") if e_deadline_on else None
                        e_notes = st.text_area("NOTES", value=task.get("notes", ""), key=f"edit-notes-{series_id}")
                        save_edit = st.form_submit_button("UPDATE ENTIRE SERIES")
                    if save_edit:
                        try:
                            store.update_series(
                                series_id, title=e_title, category=e_category,
                                priority=e_priority, start_time=e_start.strftime("%H:%M"),
                                end_time=e_end.strftime("%H:%M"),
                                deadline=e_deadline.isoformat() if e_deadline else None,
                                notes=e_notes,
                            )
                            st.success("Activity series updated.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                    if st.button("DELETE ENTIRE SERIES", key=f"delete-series-{series_id}"):
                        store.delete_series(series_id)
                        st.rerun()

    if store is not None:
        _download_exports(store, tasks, first, last, period.lower())


def show_analytics(store: SQLiteStore | SupabaseStore | None, selected: date) -> None:
    end_date = selected
    start_date = selected - timedelta(days=29)
    st.markdown('<div class="eyebrow">DATA ANALYSIS / 30-DAY WINDOW</div>', unsafe_allow_html=True)
    st.title("Time-use analysis")
    tasks = store.get_tasks(start_date, end_date) if store is not None else [
        row for row in demo_tasks(start_date, end_date)
        if start_date <= date.fromisoformat(row["event_date"]) <= end_date
    ]
    frame = tasks_to_frame(tasks)
    metrics = summary_metrics(frame)
    st.caption("SYNTHETIC DATA · Demonstration records only." if store is None else f"{start_date.isoformat()} → {end_date.isoformat()} · Based on your recorded schedule.")
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("OCCURRENCES", metrics["tasks"])
    x2.metric("PLANNED", f"{metrics['planned_hours']:.1f} h")
    x3.metric("COMPLETED", metrics["completed"])
    x4.metric("COMPLETION", f"{metrics['completion_rate']:.0f}%")
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    if frame.empty:
        st.info("No activity data yet. Add activities in the planner; analysis is generated from your records.")
        return

    left, right = st.columns(2)
    category_data = time_by_category(frame)
    category_fig = go.Figure(go.Bar(
        x=category_data["hours"], y=category_data["category"], orientation="h",
        marker_color="#9d9277", text=category_data["hours"].map(lambda v: f"{v:.1f} h"), textposition="outside",
    ))
    category_fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Hours", title="TIME BY CATEGORY")
    left.plotly_chart(plot_theme(category_fig), use_container_width=True, config={"displayModeBar": False})
    weekday_data = time_by_weekday(frame)
    weekday_fig = go.Figure(go.Bar(
        x=weekday_data["day"], y=weekday_data["hours"], marker_color="#687989",
        text=weekday_data["hours"].map(lambda v: f"{v:.1f}"), textposition="outside",
    ))
    weekday_fig.update_layout(yaxis_title="Hours", title="SCHEDULED TIME BY WEEKDAY")
    right.plotly_chart(plot_theme(weekday_fig), use_container_width=True, config={"displayModeBar": False})
    heat = activity_heatmap(frame)
    heat_fig = go.Figure(go.Heatmap(
        z=heat.values, x=[f"{hour:02d}:00" for hour in heat.columns], y=heat.index,
        colorscale=[[0, "#11161c"], [0.35, "#45515d"], [1, "#c0ad83"]],
        colorbar=dict(title="min", tickfont=dict(color="#89939d")),
        hovertemplate="%{y} · %{x}<br>%{z:.0f} min<extra></extra>",
    ))
    heat_fig.update_layout(title="ACTIVITY DISTRIBUTION / WEEKDAY × HOUR", xaxis_title="Local time", yaxis_title="")
    st.plotly_chart(plot_theme(heat_fig, 340), use_container_width=True, config={"displayModeBar": False})
    st.caption("Descriptive summaries of scheduled blocks, not measures of productivity, quality, or biological performance. Overlapping activities are counted independently.")

    if store is not None:
        reflections = store.get_reflections(start_date, end_date)
        if reflections:
            ref_frame = pd.DataFrame(reflections)
            ref_frame["entry_date"] = pd.to_datetime(ref_frame["entry_date"])
            ref_frame["cholqij_name"] = ref_frame["entry_date"].dt.date.map(lambda d: convert_date(d).cholqij_name)
            ref_frame["cholqij"] = ref_frame["entry_date"].dt.date.map(lambda d: convert_date(d).cholqij)
            st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
            st.markdown('<div class="eyebrow">SELF-REPORTED DATA / EXPLORATORY</div>', unsafe_allow_html=True)
            st.caption("Personal energy ratings by calendar day. Self-selected observations; no causal inference.")
            st.dataframe(ref_frame[["entry_date", "cholqij", "mood", "energy", "note"]], hide_index=True, use_container_width=True)
        _download_exports(store, store.get_tasks(date(1900, 1, 1), date(2200, 12, 31)), date(1900, 1, 1), date(2200, 12, 31), "all-data")


def show_method() -> None:
    st.markdown('<div class="eyebrow">PROJECT SPECIFICATION / V0.2</div>', unsafe_allow_html=True)
    st.title("Method & framework")
    st.markdown("""
**MAYA TIME** is a personal calendar calculator and time-use information system. It joins five distinct layers:

| Layer | Representation | Evidence status |
|---|---|---|
| Gregorian | Civil dates, time zones, deadlines and time blocks | Deterministic civil-calendar arithmetic |
| K'iche' Cholq'ij | 13 coefficients × 20 day names | Calendar arithmetic under GMT 584283 alignment |
| Astronomical sky | Geocentric ecliptic positions and lunar phase | Model-based astronomical calculations |
| Personal time-use | Recurring activity series and dated occurrences | User-entered observational records |
| Symbolic reflection | Personal notes and optional astrological meaning | Subjective interpretation; not a scientific causal model |

### Temporal model

A recurring activity is stored as one **activity series** and expanded into dated **occurrences**. Supported recurrence rules are once, daily, weekly (selected weekdays), and monthly (same day-of-month; months without that date are skipped). Completion belongs to an occurrence, while title, category, priority and time block belong to the series.

### Persistence and privacy

Local mode uses SQLite. Hosted mode uses Supabase PostgreSQL with Supabase Auth and Row Level Security (RLS). Each row is tied to `auth.uid()`; the app uses a publishable/anon key and never requires a service-role key. The SQL migration is in `supabase/schema.sql`. Excel exports are generated from query results and are not a second source of truth.

### Data analysis

Duration is calculated as `end − start`. Analysis aggregates planned minutes by category, weekday and hour. Completion rate is completed occurrences divided by all occurrences in the selected period. These are descriptive metrics; they do not measure the quality or value of work. Repeated occurrences are counted separately; overlapping blocks are not deduplicated.

### Astronomical and astrological separation

Planetary and lunar positions are calculated as geocentric ecliptic coordinates at 12:00 in the America/Guatemala time zone. Tropical zodiac signs divide the ecliptic into twelve equal 30° sectors. Astronomical positions are calculations; astrological meanings and claims about mood or events are symbolic interpretations and are not scientifically established.

### Cultural boundary

Cholq'ij is a living Maya calendar, not merely a historical algorithm. Spellings, local practice and alignments can vary. This prototype exposes its GMT convention and does not claim to replace the knowledge or authority of Ajq'ijab' or Maya communities.

### Reproducibility

The same Gregorian input and correlation constant produce the same calendar result. Regression tests cover the anchor date 21 December 2012 and the published cross-check 23 May 2020 = 10 Tz'i' under GMT 584283. Recurrence expansion and activity aggregation are deterministic functions tested independently of the interface.
""")
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("**Implementation references**")
    st.markdown("""
- Smithsonian National Museum of the American Indian, [The Calendar System](https://maya.nmai.si.edu/calendar/calendar-system).
- William H. Mex, [Fórmula para el cálculo manual de fechas del Tzolk’in / Cholq’ij](https://filosofiamaya.com/2020/05/23/formula-para-el-calculo-manual-de-la-fecha-tzolkin-cholqij/) (2020).
- Carlos Barrera Atuesta, [El sistema de correlaciones de los calendarios mayas clásico y k'iche'](https://doi.org/10.1344/BA2022.84.1001), *Boletín Americanista* (2022).
- [Astronomy Engine](https://github.com/cosinekitty/astronomy), MIT-licensed calculations.
- [Supabase Python documentation](https://supabase.com/docs/reference/python/introduction) and [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).
- [Streamlit fragments](https://docs.streamlit.io/develop/concepts/architecture/fragments) and [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).
""")


def show_supabase_auth() -> tuple[Any, str] | None:
    supabase_url = setting("SUPABASE_URL")
    supabase_key = setting("SUPABASE_PUBLISHABLE_KEY") or setting("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        st.error("Supabase mode is selected, but SUPABASE_URL or SUPABASE_KEY is missing. Add them to Streamlit secrets; see .streamlit/secrets.toml.example.")
        st.stop()
    try:
        from supabase import create_client
        if "maya_supabase_client" not in st.session_state:
            st.session_state.maya_supabase_client = create_client(supabase_url, supabase_key)
        client = st.session_state.maya_supabase_client
    except Exception as exc:
        st.error(f"Could not initialize Supabase: {exc}")
        st.stop()

    user_id = st.session_state.get("maya_supabase_user_id")
    if user_id:
        return client, str(user_id)

    st.markdown('<div class="eyebrow">PRIVATE STORAGE / SUPABASE AUTH</div>', unsafe_allow_html=True)
    st.title("MAYA TIME / ACCOUNT ACCESS")
    st.caption("Your activities and reflections are private to the account that signs in.")
    login_tab, signup_tab = st.tabs(["SIGN IN", "CREATE ACCOUNT"])
    with login_tab:
        with st.form("supabase_sign_in"):
            email = st.text_input("EMAIL", key="login_email")
            password = st.text_input("PASSWORD", type="password", key="login_password")
            login = st.form_submit_button("SIGN IN", type="primary")
        if login:
            try:
                response = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
                st.session_state.maya_supabase_user_id = response.user.id
                st.session_state.maya_supabase_email = response.user.email
                st.rerun()
            except Exception:
                st.error("Sign-in failed. Check the email/password and confirm the email address if verification is enabled.")
    with signup_tab:
        with st.form("supabase_sign_up"):
            new_email = st.text_input("EMAIL", key="signup_email")
            new_password = st.text_input("PASSWORD", type="password", key="signup_password")
            confirm_password = st.text_input("CONFIRM PASSWORD", type="password", key="signup_password_confirm")
            signup = st.form_submit_button("CREATE ACCOUNT", type="primary")
        if signup:
            if new_password != confirm_password:
                st.error("The passwords do not match.")
            elif len(new_password) < 8:
                st.error("Use a password with at least 8 characters.")
            else:
                try:
                    response = client.auth.sign_up({"email": new_email.strip(), "password": new_password})
                    if response.session and response.user:
                        st.session_state.maya_supabase_user_id = response.user.id
                        st.session_state.maya_supabase_email = response.user.email
                        st.rerun()
                    st.success("Account created. Check your email to confirm the address, then sign in here.")
                except Exception:
                    st.error("Account creation failed. Check the email, password requirements and Supabase Auth settings.")
    st.caption("Security: the app uses Supabase Auth and row-level security. Never paste a service-role key into this app or a public repository.")
    return None


def main() -> None:
    store: SQLiteStore | SupabaseStore | None = None
    if STORAGE_MODE == "local":
        if "maya_local_store" not in st.session_state:
            st.session_state.maya_local_store = SQLiteStore()
        store = st.session_state.maya_local_store
    elif STORAGE_MODE == "supabase":
        auth = show_supabase_auth()
        if auth is None:
            st.stop()
        client, user_id = auth
        store = SupabaseStore(client, user_id)

    st.sidebar.markdown("<div class='eyebrow'>MAYA TIME / 001</div>", unsafe_allow_html=True)
    st.sidebar.markdown("# ◌ MAYA TIME")
    st.sidebar.caption("CALENDAR · TIME · DATA")
    page = st.sidebar.radio("NAVIGATION", ["OVERVIEW", "WEEK PLANNER", "ANALYTICS", "METHOD"], label_visibility="collapsed")
    st.sidebar.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.sidebar.caption(f"CORRELATION 584283 · GMT\n\nSTORAGE: {STORAGE_MODE.upper()}")
    if STORAGE_MODE == "supabase" and st.session_state.get("maya_supabase_email"):
        st.sidebar.caption(st.session_state.maya_supabase_email)
        if st.sidebar.button("SIGN OUT", use_container_width=True):
            try:
                st.session_state.maya_supabase_client.auth.sign_out()
            except Exception:
                pass
            for key in ["maya_supabase_user_id", "maya_supabase_email", "maya_supabase_client"]:
                st.session_state.pop(key, None)
            st.rerun()
    st.sidebar.caption("SOURCE · GITHUB REPOSITORY")

    render_mission_clock()
    selected = render_date_navigation()
    st.markdown('<div class="eyebrow">PERSONAL TIME SYSTEM / GUATEMALA</div>', unsafe_allow_html=True)
    if page == "OVERVIEW":
        st.title("Time, made legible.")
        show_overview(store, selected)
    elif page == "WEEK PLANNER":
        show_planner(store, selected)
    elif page == "ANALYTICS":
        show_analytics(store, selected)
    else:
        show_method()
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.caption("MAYA TIME · PERSONAL TEMPORAL INFORMATION SYSTEM · v0.2.1")


if __name__ == "__main__":
    main()
