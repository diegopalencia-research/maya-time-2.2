# Supabase configuration

This guide connects a MAYA TIME deployment to private PostgreSQL storage.

## 1. Create the project

Create a project at <https://supabase.com/>. Select a strong database password and save it in your password manager. The application does not need the database password.

## 2. Create tables and policies

Open **SQL Editor → New query** in the Supabase dashboard. Run the complete contents of `supabase/schema.sql`. This creates:

- `activity_series`
- `activity_occurrences`
- `reflections`

Row Level Security is enabled on all three tables. All policies restrict rows to the authenticated owner (`auth.uid() = user_id`).

## 3. Configure the app key

Open **Project Settings → API Keys** or the Project **Connect** panel. Copy the Project URL and the publishable key (prefix commonly `sb_publishable_`). The legacy `anon` key is accepted too. Do not use a `service_role` or secret key.

For local use, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in values. That real secrets file is ignored by Git.

For Streamlit Community Cloud, set these under **App → Settings → Secrets**:

```toml
MAYA_TIME_STORAGE = "supabase"
SUPABASE_URL = "https://YOUR-PROJECT-REF.supabase.co"
SUPABASE_KEY = "YOUR_PUBLISHABLE_KEY"
```

## 4. Create your MAYA TIME login

Open the app, select **Create account**, and register using your email. If email confirmation is enabled in Supabase Auth, confirm the email before signing in. The password is handled by Supabase Auth; MAYA TIME does not store it.

## 5. Security checklist

- Never commit `.streamlit/secrets.toml`.
- Never put a service-role key in Streamlit secrets for this application.
- Keep the RLS policies in place.
- Do not remove `user_id` filters or RLS policies.
- Use separate Supabase accounts for separate users; RLS enforces row ownership.
- Exported XLSX/CSV files contain personal data. Store them privately.

## 6. Free plan considerations

Supabase's Free plan is useful for a prototype and a personal project, but it has quotas and free projects may pause after a period of low activity. Confirm current plan details in the Supabase dashboard before relying on the app as an always-on service.
