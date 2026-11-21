# Methodology and calculation specification

## 1. Gregorian → Julian Day Number

For a Python `datetime.date` value `d`, the app uses:

`JDN = d.toordinal() + 1,721,425`

This integer is the Julian Day Number assigned to Gregorian midnight for the selected civil date.

## 2. Correlation convention

The default constant is:

`GMT = 584,283`

The number of elapsed days from the Long Count epoch is:

`N = JDN - 584,283`

The correlation is a declared model parameter, not a property of the Gregorian calendar. Alternative values have been proposed; GMT 584285 is two days offset from GMT 584283 and can produce a different Cholq'ij alignment.

## 3. Cholq'ij

The coefficient is:

`coefficient = ((N + 3) mod 13) + 1`

The day-name position is:

`name_index = (N + 19) mod 20`

The app uses the K'iche' name sequence stored in `data/kiche_day_signs.csv`:

`Imox, Iq', Aq'ab'al, K'at, Kan, Kame, Kej, Q'anil, Toj, Tz'i', B'atz', E, Aj, I'x, Tz'ikin, Ajmaq, No'j, Tijax, Kawoq, Ajpu`.

The day-name crosswalk follows the equivalence mapping published in William H. Mex's 2020 explanation of the GMT 584283 calculation. A day-number/name pair repeats after 260 days.

## 4. Haab'

The fixed-cycle Haab' position is calculated as:

`H = (N + 348) mod 365`

For `H < 360`, month and day are obtained by division by 20. For `H ≥ 360`, the date is in Wayeb' (days 0–4). This is the standard GMT/Classic Haab' output used as a reference layer; it should not be mistaken for every regional contemporary Ab' practice.

## 5. Long Count

The elapsed day count `N` is decomposed with mixed-radix units:

- 1 k'in = 1 day
- 1 winal = 20 k'in
- 1 tun = 18 winal = 360 days
- 1 k'atun = 20 tun = 7,200 days
- 1 bak'tun = 20 k'atun = 144,000 days

The output order is `bak'tun.k'atun.tun.winal.k'in`.

## 6. Calendar Round

The combined Haab' and Cholq'ij alignment repeats after:

`LCM(260, 365) = 18,980 days`

The application reports the position within this 18,980-day interval.

## 7. Astronomical positions and sky visualizations

The sky module calculates the selected date at 12:00 local time in `America/Guatemala`, then converts the timestamp to UTC. It uses Astronomy Engine:

- Sun: geocentric apparent ecliptic coordinates.
- Moon: geocentric ecliptic longitude, phase angle and modeled illuminated fraction.
- Planets: geocentric vectors transformed into true ecliptic coordinates of date.
- Tropical sign: `floor(longitude / 30°)`; each sign is an equal 30° sector and is not an IAU constellation boundary.
- Apparent daily motion: shortest signed angular difference between the selected instant and 24 hours later.

The zodiac wheel is a geocentric display of apparent ecliptic longitude. Aspect angles are calculated from pairwise differences in those longitudes. The default major-aspect set is conjunction (0°), sextile (60°), square (90°), trine (120°) and opposition (180°), with a 6° orb threshold. The accompanying text is traditional astrological symbolism only. It is editorial context, not an empirically established planetary influence or a prediction about the user.

The scientific spatial view uses `HelioVector` positions transformed from the J2000 mean equator (EQJ) into the J2000 mean ecliptic (ECL) reference frame. The Sun is the origin; XYZ coordinates and Sun distance are expressed in astronomical units (AU). The dashboard plots X/Y and exposes Z in hover details. Dotted circular lines are mean orbital-radius guides derived from approximate semi-major axes; they are not ephemeris-computed orbital paths. The map is a two-dimensional projection of three-dimensional positions and is not to scale in planet size.

The lunar graph samples the model's illuminated fraction every three hours across a 30-day window centered on the selected date. New Moon, First Quarter, Full Moon and Last Quarter markers use the engine's lunar-quarter event search. Illumination is a modeled apparent fraction, not a direct measurement.

A negative apparent daily longitude change for a planet is labelled `R` (retrograde). The Sun and Moon are not assigned retrograde labels in this interface. Astronomy outputs are model results, not observations or spacecraft-navigation products. The project keeps astronomical coordinates, traditional astrological symbolism and personal reflection as distinct information layers.

## 8. Time-use analytics

For each task, scheduled duration is `end − start` on the same Gregorian date. The first release does not support overnight blocks. Category and weekday totals sum scheduled minutes. The heatmap allocates the minutes of each block to each local clock-hour cell it overlaps.

Completion rate is:

`100 × completed_blocks / all_blocks`

This is a planning-status metric, not a validated productivity score. Overlapping tasks are counted independently; the app does not silently deduplicate them.

## 9. Validation anchors

| Gregorian date | Expected GMT 584283 output | Purpose |
|---|---|---|
| 2012-12-21 | Long Count 13.0.0.0.0; 4 Ajpu; Haab' 3 K'ank'in | Smithsonian Calendar Round anchor, with K'iche' day-name equivalence |
| 2020-05-23 | 10 Tz'i' | Published highland K'iche' equivalent in Mex (2020) |

Tests also verify cycle periods: 260, 365, and 18,980 days.

## 10. Known limitations

- One correlation convention is implemented by default; local/regional K'iche' calendar practice can differ.
- The GMT 584283 correlation is debated in scholarship; the interface exposes the assumption.
- The Haab' implementation follows the Classic GMT arithmetic, not every living highland Ab' practice.
- The app contains no authoritative spiritual or divinatory interpretation of individual day signs.
- Astronomical model output is not an observational instrument or spacecraft-navigation product.
- Task records are personal observations and should not be interpreted causally.

## 11. Recurrence expansion

The recurrence engine accepts a start date, an inclusive end date, a frequency and (for weekly schedules) a set of weekdays. It deterministically returns concrete dates. Monthly recurrence preserves the numerical day of the month and skips a month when the day does not exist. Expansion is limited to 732 occurrences per creation request to prevent accidental excessive writes. Completion status is stored per occurrence; edits to the series definition update its shared activity metadata.

## 12. Storage and export

Local records are stored in SQLite. Hosted records are stored in Supabase PostgreSQL. Hosted access uses Supabase Auth and RLS policies requiring `auth.uid() = user_id` on the activity series, occurrence and reflection tables. The application uses a publishable key and an authenticated session, not a service-role key. Export files are generated in memory from database query results and contain six sheets: Occurrences, Activity series, Deadlines, Reflections, Time by category, and Time by weekday.
