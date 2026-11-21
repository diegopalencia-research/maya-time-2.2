# MAYA TIME: A Gregorian–Cholq'ij Calculator and Personal Temporal Information System

**Author:** Diego José Palencia Robles  
**Version:** 0.2.1  
**Document type:** Technical note / software specification  
**Status:** Working prototype

## Abstract

MAYA TIME is a lightweight Streamlit application for converting Gregorian dates into a documented K'iche' Cholq'ij alignment and organizing personal activities. It uses GMT 584283 as an explicit baseline, calculates corresponding Classic Haab' and Long Count values, and documents the cultural and correlation limitations. A live chronometer displays Guatemala local time and UTC, the operational time standard used by the International Space Station. The Overview includes a geocentric tropical-zodiac wheel, a separate heliocentric J2000 ecliptic XY projection with XYZ hover data, traditional symbolic aspect notes, and a modeled lunar-illumination curve with quarter-phase markers. The planner supports once, daily, weekly and monthly activity recurrence, independent occurrence completion, deadlines, daily reflection, descriptive time-use analysis, and Excel/CSV exports. Hosted personal storage is implemented with Supabase Auth and PostgreSQL Row Level Security; local use relies on SQLite. The project is designed as a reproducible personal tool and a portfolio demonstration of software engineering, data modeling, data analysis, visualization and information design.

## 1. Problem statement

Civil calendars support dates, work schedules and deadlines but do not display the recurring Cholq'ij cycle. A separate calendar reference and a separate weekly planner create friction when moving between calendar systems and practical time allocation. MAYA TIME places these functions in one compact instrument while keeping their different evidence status explicit.

## 2. Objective

Implement a minimal web application that:

1. converts a selected Gregorian date into a declared Maya calendar alignment;
2. displays the 260-day cycle position and selected recurrence markers;
3. displays Guatemala local time and UTC independently of the selected calendar date;
4. creates and manages activity series and their dated occurrences;
5. generates descriptive visualizations and Excel/CSV extracts from user-entered records; and
6. optionally displays astronomical positions with an explicitly symbolic astrological interpretation layer.

## 3. Research question

How can Gregorian planning, the K'iche' Cholq'ij cycle, astronomical position data and personal time-use records be presented in one reproducible and minimal digital instrument without conflating their evidence status?

## 4. System design

- `app.py`: Streamlit interface, chronometer, date navigation, planner, analytics and authentication entry point.
- `calendar_engine.py`: Julian Day Number, Cholq'ij, Haab', Long Count and cycle calculations.
- `astronomy_layer.py`: geocentric tropical longitudes, heliocentric XYZ vectors, lunar illumination samples, lunar-quarter events and longitude-based aspect calculations through Astronomy Engine; symbolic interpretation text is kept explicitly non-scientific.
- `planner_logic.py`: deterministic daily, weekly and monthly recurrence expansion.
- `storage.py`: per-session SQLite or authenticated Supabase persistence.
- `analytics.py`: derived durations, category and weekday aggregation, and activity heatmap preparation.
- `exports.py`: multi-sheet Excel and CSV data products.
- `supabase/schema.sql`: PostgreSQL tables, constraints, grants and RLS policies.

## 5. Calendar and astronomy methods

The calendar engine applies `N = JDN − 584283`. It computes the Cholq'ij number with `((N + 3) mod 13) + 1` and the K'iche' day-name position with `(N + 19) mod 20`. Haab' and Long Count values are calculated under the same declared GMT alignment. Details and limitations are in [METHODOLOGY.md](METHODOLOGY.md).

Geocentric positions are model-based ecliptic outputs at the specified local-noon instant. Tropical zodiac signs divide the ecliptic into twelve equal 30° sectors. The zodiac wheel and heliocentric map use separate coordinate frames. Heliocentric XYZ values are expressed in the J2000 mean ecliptic frame and AU. The lunar curve is modeled illumination sampled over a 30-day window. Astrological aspect descriptions are traditional symbolic interpretations, not evidence that planetary positions cause mood, productivity or events. See [METHODOLOGY.md](METHODOLOGY.md) for coordinate and visualization details.

## 6. Activity and recurrence model

A recurring activity is stored as an `activity_series` row plus dated `activity_occurrences` rows. The series holds shared attributes (title, category, priority, start/end time, deadline and recurrence rule); occurrences hold the calendar date and independent completion status.

- Once: one occurrence on the selected start date.
- Daily: every date from start through repeat-until, inclusive.
- Weekly: selected weekdays from start through repeat-until, inclusive (Monday = 0 through Sunday = 6).
- Monthly: same day-of-month; months that do not contain that date are skipped rather than shifted silently.

A creation operation is capped at 732 occurrences. Editing series metadata updates the shared definition; completion and deletion can be applied to an individual occurrence, while deleting the series removes all of its occurrences.

## 7. Storage, security and exports

Local mode uses SQLite. Hosted mode uses Supabase PostgreSQL and Supabase Auth. RLS policies restrict rows to `auth.uid() = user_id`; a composite foreign key also ensures an occurrence belongs to a series owned by the same user. The app uses a publishable/legacy anon key with an authenticated session and does not require a service-role key. The public demo uses synthetic records and does not persist visitor data.

Excel exports are generated from query results and contain Occurrences, Activity series, Deadlines, Reflections, Time by category and Time by weekday. CSV export provides a flat occurrence-level dataset. Excel is an export format, not a second operational database.

## 8. Data analysis and limitations

Task duration is computed from scheduled start and end times. Descriptive summaries include hours by category, hours by weekday, scheduled minutes by local clock-hour cell and completion status. Completion rate is completed occurrences divided by all occurrences in the selected period. These are planning metrics, not productivity or cognitive-performance measures. Overlapping tasks are counted independently and overnight blocks are not supported in this release.

The GMT correlation is a documented but debated convention. Scholarship distinguishes Classic and K'iche' calendrical correlations; this prototype does not implement every regional or contemporary calendar practice. The day-name crosswalk and selected anchor require careful treatment and should not be presented as universally authoritative.

Personal reflection records are subjective, self-reported and exploratory. They do not establish causal effects of calendar signs, planetary positions or astrological movements.

## 9. Validation

Regression tests cover published calendar anchors, the cycle periods (260, 365 and 18,980 days), task-duration arithmetic, time-hour aggregation, recurrence generation, SQLite CRUD, legacy task migration and Excel workbook structure. One astronomy test requires the optional Astronomy Engine dependency to be installed. GitHub Actions runs the automated suite on pushes and pull requests.

## 10. Expected contribution

The deliverable is a working, transparent software instrument with tests, documentation, a relational data model, recurrence logic, analytical functions, Excel/CSV export and a minimalist interface. It demonstrates the complete path from temporal data to a usable tool and portfolio-quality information design.

## References

1. Smithsonian National Museum of the American Indian. [The Calendar System](https://maya.nmai.si.edu/calendar/calendar-system). *Living Maya Time*.
2. Mex, W. H. (2020). [Fórmula para el cálculo manual de fechas del Tzolk’in / Cholq’ij](https://filosofiamaya.com/2020/05/23/formula-para-el-calculo-manual-de-la-fecha-tzolkin-cholqij/).
3. Barrera Atuesta, C. (2022). [El sistema de correlaciones de los calendarios mayas clásico y k'iche'](https://doi.org/10.1344/BA2022.84.1001). *Boletín Americanista*, 84.
4. [Astronomy Engine](https://github.com/cosinekitty/astronomy). Open-source planetary and lunar calculations; MIT License.
5. [Supabase Python documentation](https://supabase.com/docs/reference/python/introduction) and [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).
6. [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).
