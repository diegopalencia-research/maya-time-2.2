# MAYA TIME

**A Gregorian–Cholq'ij calendar calculator and personal temporal information system.**

MAYA TIME combines Gregorian civil time, a documented K'iche' Cholq'ij alignment, astronomical positions, recurring personal activities, and descriptive time-use analytics in a restrained Streamlit interface.

> Calendar arithmetic is deterministic under the stated GMT 584283 convention. Astronomy, Maya cultural knowledge, personal reflection, and astrological interpretation are kept as distinct information layers.

## Interface

- **Mission clock** — live Guatemala local time and UTC / ISS operations time (Zulu). ISS operations use UTC; the dashboard does not invent a separate ISS time zone.
- **Date navigation** — previous day, next day, direct date selection, and Today. The selected date is independent of the live clock.
- **Overview** — Gregorian date, Cholq'ij, Classic GMT Haab', Long Count, cycle markers and a Sky Observatory with a geocentric zodiac wheel, heliocentric scientific XY map, symbolic aspect notes and a modeled lunar-illumination curve.
- **Activity planner** — once, daily, weekly (selected weekdays), or monthly activities; time blocks, categories, priorities, deadlines, completion, editing and deletion.
- **Analytics** — planned time by category and weekday, weekday × hour heatmap, completion rate, and reflection summaries.
- **Excel export** — formatted `.xlsx` workbook with Occurrences, Activity series, Deadlines, Reflections, Time by category, and Time by weekday sheets. CSV export is also available.
- **Method** — theory, mathematical conventions, recurrence logic, data architecture, validation and limitations.

## Quick start — Windows 11 (local SQLite, no account required)

1. Install Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/).
2. Extract or clone this repository.
3. Double-click `setup_windows.bat` once. It creates a virtual environment, installs dependencies, and starts the local application.
4. For later local sessions, double-click `run_local.bat`.
5. To use your Supabase project from the same computer, configure `.streamlit/secrets.toml` and double-click `run_supabase.bat`.

Manual commands from the repository folder:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:MAYA_TIME_STORAGE = "local"
python -m streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). Local planner data is stored in `data/maya_time.sqlite3`, which is excluded from Git.

## Supabase setup — private hosted storage

Use Supabase when you deploy the app publicly and want your own schedule, recurring activity data and reflections to persist privately. The application uses Supabase Auth and PostgreSQL Row Level Security (RLS); users can only access rows carrying their own authenticated `user_id`.

1. Create a free project at [supabase.com](https://supabase.com/). The Free plan is suitable for an initial personal project (subject to its quotas and inactivity pausing policy).
2. In the Supabase project, open **SQL Editor → New query**.
3. Open `supabase/schema.sql` from this repository, copy all SQL into the editor, and run it once.
4. In **Project Settings → API Keys** (or the project **Connect** panel), copy the Project URL and the **publishable key**. A legacy `anon` key is also accepted. **Never use or expose the `service_role` / secret key.**
5. For local Supabase development, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, then replace the placeholder values:

```toml
MAYA_TIME_STORAGE = "supabase"
SUPABASE_URL = "https://YOUR-PROJECT-REF.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_PUBLISHABLE_KEY"
```

6. Run `python -m streamlit run app.py`. Create your personal MAYA TIME account in the app. If email confirmation is enabled in Supabase Auth, confirm the message before signing in.
7. For hosted deployment, add the same three values under **App → Settings → Secrets** in Streamlit Community Cloud. Do not upload `secrets.toml` to GitHub.

### Supabase free-plan note

Supabase currently offers a Free plan with two free projects and 500 MB database size per project. Free projects may pause after a week of low activity. This is appropriate for testing and a personal portfolio demo, but do not treat the free tier as a guaranteed always-on production service. Check current plan details before relying on it.

## Deploy to Streamlit Community Cloud

1. Create a **public GitHub repository** named `maya-time`.
2. Upload the contents of this folder to the repository root, including `.streamlit/config.toml`.
3. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
4. Choose **Create app** and select the `maya-time` repository, branch `main`, and entrypoint file `app.py`.
5. For a public demo with synthetic data, leave storage mode at `demo`. For your private account, configure Supabase secrets as described above and set `MAYA_TIME_STORAGE = "supabase"`.
6. Deploy.

**Privacy:** Demo mode uses synthetic records and does not persist visitors' activities or reflections. Local mode uses a local SQLite file. Hosted personal mode requires Supabase Auth and RLS. Never set a public hosted deployment to shared SQLite mode and never add private data, database files, passwords, publishable keys, or service keys to Git.

## GitHub upload using Git

Run these commands from the extracted project directory after creating the empty GitHub repository:

```bash
git init
git add .
git commit -m "MAYA TIME v0.2.1 — Sky Observatory"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/maya-time.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Data model

The source-of-truth model is relational:

| Table | Grain | Main role |
|---|---|---|
| `activity_series` | One row per activity definition | Title, category, time, priority, deadline and recurrence rule |
| `activity_occurrences` | One row per scheduled date | Event date and completion status, owner-linked to its series |
| `reflections` | One row per user/date | Self-described mood, energy and note |

Weekly recurrence stores selected weekdays (Monday = 0 through Sunday = 6). Monthly recurrence uses the same day-of-month and skips months that do not contain that date (for example, a monthly event on the 31st is not shifted to the 30th). Occurrence expansion is deterministic and limited to 732 records per creation operation to prevent accidental large writes.

SQLite and Supabase implement the same logical model. Excel files are generated from database query results; Excel is an export format, not a second operational database.

## Technical structure

```text
maya-time/
├── app.py
├── calendar_engine.py
├── astronomy_layer.py
├── analytics.py
├── planner_logic.py
├── storage.py
├── exports.py
├── data/kiche_day_signs.csv
├── supabase/schema.sql
├── docs/
│   ├── THEORETICAL_FRAMEWORK.md
│   ├── METHODOLOGY.md
│   ├── TECHNICAL_NOTE.md
│   └── SUPABASE_SETUP.md
├── tests/
├── .github/workflows/tests.yml
├── .streamlit/config.toml
├── .streamlit/secrets.toml.example
├── requirements.txt
└── requirements-dev.txt
```

## Validation

Run locally:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Calendar anchors under GMT 584283:

| Gregorian | Expected |
|---|---|
| 2012-12-21 | 13.0.0.0.0 · 4 Ajpu · 3 K'ank'in |
| 2020-05-23 | 10 Tz'i' |

Additional tests cover 260-, 365-, and 18,980-day cycles, recurrence expansion, SQLite CRUD and migration from the v0.1.0 tasks table, and Excel workbook structure.

## Portfolio skills demonstrated

Python · Streamlit · time-zone handling · calendar algorithms · PostgreSQL · SQL schema design · authentication · row-level security · SQLite · data modeling · recurrence algorithms · CRUD · Pandas · exploratory data analysis · Plotly · Excel automation · information design · unit testing · Git/GitHub · CI.

## License

MIT. See [LICENSE](LICENSE). Astronomy Engine is a separate MIT-licensed dependency; see its [source repository](https://github.com/cosinekitty/astronomy).
