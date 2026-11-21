-- MAYA TIME / Supabase PostgreSQL schema
-- Run once in Supabase Dashboard > SQL Editor.
-- This schema uses Supabase Auth + Row Level Security. Do NOT use service_role keys.

create extension if not exists pgcrypto;

create table if not exists public.activity_series (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (length(trim(title)) > 0),
    category text not null,
    priority smallint not null default 2 check (priority between 1 and 3),
    start_date date not null,
    start_time time not null,
    end_time time not null,
    frequency text not null default 'once'
        check (frequency in ('once', 'daily', 'weekly', 'monthly')),
    weekdays smallint[] not null default '{}',
    repeat_until date not null,
    deadline date,
    notes text not null default '',
    created_at timestamptz not null default now(),
    constraint activity_series_time_check check (end_time > start_time),
    constraint activity_series_dates_check check (repeat_until >= start_date),
    constraint activity_series_id_user_id_unique unique (id, user_id),
    constraint activity_series_weekdays_check check (
        weekdays <@ array[0,1,2,3,4,5,6]::smallint[]
    )
);

create table if not exists public.activity_occurrences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    series_id uuid not null,
    event_date date not null,
    completed boolean not null default false,
    created_at timestamptz not null default now(),
    unique (series_id, event_date),
    constraint occurrence_owner_series_fk foreign key (series_id, user_id)
        references public.activity_series(id, user_id) on delete cascade
);

create table if not exists public.reflections (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    entry_date date not null,
    mood text not null default '',
    energy smallint not null default 3 check (energy between 1 and 5),
    note text not null default '',
    updated_at timestamptz not null default now(),
    unique (user_id, entry_date)
);

create index if not exists idx_activity_occurrences_user_date
    on public.activity_occurrences(user_id, event_date);
create index if not exists idx_activity_series_user_start
    on public.activity_series(user_id, start_date);
create index if not exists idx_reflections_user_date
    on public.reflections(user_id, entry_date);

alter table public.activity_series enable row level security;
alter table public.activity_occurrences enable row level security;
alter table public.reflections enable row level security;

drop policy if exists "series owner only" on public.activity_series;
create policy "series owner only" on public.activity_series
    for all to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "occurrence owner only" on public.activity_occurrences;
create policy "occurrence owner only" on public.activity_occurrences
    for all to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "reflection owner only" on public.reflections;
create policy "reflection owner only" on public.reflections
    for all to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

grant select, insert, update, delete on public.activity_series to authenticated;
grant select, insert, update, delete on public.activity_occurrences to authenticated;
grant select, insert, update, delete on public.reflections to authenticated;
revoke all on public.activity_series from anon;
revoke all on public.activity_occurrences from anon;
revoke all on public.reflections from anon;
