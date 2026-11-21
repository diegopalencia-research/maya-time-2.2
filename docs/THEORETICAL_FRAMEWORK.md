# Theoretical framework

## 1. Project definition

**MAYA TIME** is a personal calendar calculator and time-use instrument. It combines a civil calendar, a documented K'iche' Cholq'ij alignment, astronomical measurements, and a clearly separated personal-symbolic layer.

The system is designed to answer two practical questions:

1. What date and recurring calendar cycles correspond to a selected Gregorian day?
2. How is personal time being allocated across activities, goals, and deadlines?

It is also a reproducible portfolio demonstration of data processing, temporal analysis, visualization, and information design.

## 2. Conceptual model: four layers

| Layer | Input | Transformation | Output | Epistemic status |
|---|---|---|---|---|
| Civil chronology | Gregorian date/time | Calendar arithmetic | Weekday, date, deadline, time block | Deterministic convention |
| Maya calendrics | Gregorian date + correlation | JDN and cycle arithmetic | Cholq'ij, Haab', Long Count | Mathematical under declared alignment; culturally situated |
| Astronomical sky | UTC instant | Ephemeris model | Geocentric ecliptic positions, lunar phase | Model-based physical calculation |
| Personal symbolism | Calendar labels + personal entry | Reflection and interpretation | Intention, mood and notes | Subjective; not a causal scientific model |

The layers are displayed together but are not treated as equivalent kinds of evidence.

## 3. Maya calendrical model

The Cholq'ij is a 260-day count formed by the interaction of a 13-number sequence and a 20-day-name sequence. Their least common multiple is 260, so a complete number/name combination repeats after 260 days. The Haab' consists of 18 periods of 20 days and a five-day Wayeb' period (365 days). The Long Count uses mixed-radix units: 1 k'in = 1 day, 1 winal = 20 k'in, 1 tun = 18 winal (360 days), 1 k'atun = 20 tun, and 1 bak'tun = 20 k'atun.

This prototype uses the GMT 584283 correlation as its explicit baseline and a K'iche' day-name crosswalk. The GMT correlation is widely used for the Classic Maya Long Count, but the correlation and its relationship to particular contemporary highland counts have been discussed and contested. A 2022 study specifically examines differences between Classic and K'iche' calendrical correlations. Therefore, MAYA TIME reports its convention rather than presenting one output as universally authoritative for every Maya community.

The 8 B'atz' marker is calculated as the recurrence of the combination 8 + B'atz' in the 260-day count. The Smithsonian describes Wajxaqib' B'atz' as a 260-day cycle ceremony in highland Guatemala. The application does not assign prescriptive spiritual effects to the date.

## 4. Personal time-management model

A calendar block is represented as:

`(date, start, end, activity, category, priority, deadline, completion)`

Duration is calculated as:

`duration_minutes = (end_datetime - start_datetime) / 60 seconds`

The weekly planner makes intended time visible before or during execution. The analytics layer summarizes planned allocations and task status. A scheduled hour is not automatically a productive hour; the application reports time allocation, not quality, value, or cognitive performance.

## 5. Data science and information-design model

The analytical pipeline is intentionally small:

`Input → validation → structured records → derived measures → visual encoding → interpretation`

The dashboard includes:

- Category allocation: total planned hours by activity category.
- Weekday allocation: total scheduled hours by weekday.
- Activity heatmap: scheduled minutes by weekday and local clock hour.
- Completion rate: completed blocks divided by all recorded blocks.
- Cholq'ij cycle map: 13 radial levels × 20 day-name positions = 260 unique combinations.

The charts are descriptive. The user may optionally record mood, energy, and a note. Such records are self-reported observations and do not establish that a calendar sign, planet, or transit caused a mood or behaviour.

## 6. Astronomy and astrology boundary

Astronomical calculations use a published numerical ephemeris library to estimate positions of the Sun, Moon, and planets. Ecliptic longitudes are converted into tropical zodiac sectors of 30 degrees each. A retrograde label describes apparent geocentric longitudinal motion over a one-day interval; it does not mean a planet physically reverses its orbit.

Astrological meanings may be personally meaningful as a cultural or reflective practice. They are not represented as scientifically demonstrated predictors of emotion, productivity, health, or events.

## 7. Intended contribution

The contribution is a small, usable, inspectable instrument that:

- makes a specific calendar conversion reproducible;
- documents its correlation and cultural limitations;
- supports practical weekly planning;
- generates analyzable time-use records;
- presents temporal structure with minimal visual clutter; and
- keeps measurement, cultural context, and interpretation distinct.

## 8. Evaluation criteria

1. Calendar outputs match published anchor examples for the selected GMT 584283 convention.
2. The 260-day Cholq'ij combination repeats after 260 days.
3. The Haab' position repeats after 365 days under the fixed-cycle model.
4. The Calendar Round repeats after 18,980 days.
5. Task duration and aggregation results match hand-calculated test cases.
6. The application is usable without an account or external database when run locally.
7. Public demo mode does not persist visitors' tasks or reflections.


## 9. Foundational references

1. Smithsonian National Museum of the American Indian. [The Calendar System](https://maya.nmai.si.edu/calendar/calendar-system). *Living Maya Time*. Describes the 260-day Chol Q'ij, the 365-day Haab', Long Count, and the contemporary calendar context in Guatemala.
2. Barrera Atuesta, C. (2022). [El sistema de correlaciones de los calendarios mayas clásico y k'iche'](https://doi.org/10.1344/BA2022.84.1001). *Boletín Americanista*, 84. Discusses the relationship between Classic and K'iche' calendrical correlations.
3. Mex, W. H. (2020). [Fórmula para el cálculo manual de fechas del Tzolk'in / Cholq'ij](https://filosofiamaya.com/2020/05/23/formula-para-el-calculo-manual-de-la-fecha-tzolkin-cholqij/). Provides a GMT 584283 calculation example and a K'iche' day-name crosswalk used as one implementation reference.
4. [Astronomy Engine](https://github.com/cosinekitty/astronomy). MIT-licensed library for solar-system positions and lunar phase calculations.
5. [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app). Official deployment documentation.

## 10. Recurring activity and persistence model

A recurring activity is modeled as a series and its generated occurrences. The series holds stable attributes (title, category, priority, time interval, deadline, recurrence frequency and recurrence parameters); each occurrence holds a Gregorian date and independent completion status. This separation avoids duplicating the recurrence definition while allowing individual dates to be marked complete or deleted.

The supported recurrence rules are deliberately explicit:

- Once: one occurrence on the start date.
- Daily: every date from start through repeat-until, inclusive.
- Weekly: each selected weekday from start through repeat-until, inclusive (Monday = 0, Sunday = 6).
- Monthly: the same day-of-month; months without that date are skipped rather than silently moving the activity.

The database is the operational source of truth. SQLite supports local use. Supabase PostgreSQL supports hosted use with Supabase Auth and Row Level Security. Each hosted record includes a user identifier and policies restrict all reads and writes to `auth.uid() = user_id`. Occurrences use a composite foreign key to ensure their series belongs to the same user. A publishable/anonymous project key is used by the application; a service-role key is never embedded in the app.

## 11. Export and analytical data products

The Excel workbook is a reproducible extract, not a parallel database. It contains activity occurrences, activity series, deadlines, reflections, time by category, and time by weekday. CSV export provides a flat occurrence-level dataset for independent analysis. Export timestamps and date filters are derived from the same records shown in the planner.
