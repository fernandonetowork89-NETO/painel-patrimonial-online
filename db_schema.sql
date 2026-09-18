
-- PAINEL PATRIMONIAL ONLINE
-- Execute este script no SQL Editor do Supabase.
-- A aplicação usa a chave ANON e RLS. NÃO use service_role no Streamlit.

create extension if not exists pgcrypto;

create table if not exists public.positions_base (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    as_of date not null,
    asset_class text not null check (asset_class in ('Ação','FII')),
    ticker text not null,
    name text,
    quantity numeric(20,8) not null default 0,
    avg_price numeric(20,8),
    imported_price numeric(20,8),
    imported_market_value numeric(20,2),
    avg_price_undefined boolean not null default false,
    source text default 'Posição Detalhada',
    created_at timestamptz not null default now(),
    unique(user_id, as_of, asset_class, ticker)
);

create table if not exists public.portfolio_meta (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    as_of date not null,
    declared_portfolio numeric(20,2) default 0,
    declared_invested numeric(20,2) default 0,
    available_cash numeric(20,2) default 0,
    source_file text,
    imported_at timestamptz not null default now()
);

create table if not exists public.operations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    operation_date date not null,
    asset_class text not null check (asset_class in ('Ação','FII')),
    ticker text not null,
    name text,
    operation_type text not null,
    quantity numeric(20,8) default 0,
    unit_price numeric(20,8) default 0,
    costs numeric(20,2) default 0,
    institution text,
    notes text,
    origin text default 'Manual',
    external_key text,
    created_at timestamptz not null default now()
);

create unique index if not exists operations_user_external_key_uq
on public.operations(user_id, external_key)
where external_key is not null;

create table if not exists public.income (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    ticker text not null,
    asset_class text,
    income_type text not null,
    ex_date date,
    payment_date date,
    base_quantity numeric(20,8) default 0,
    amount_per_unit numeric(20,8) default 0,
    gross_amount numeric(20,2) default 0,
    tax_amount numeric(20,2) default 0,
    net_amount numeric(20,2) default 0,
    status text default 'Recebido',
    origin text default 'Manual',
    external_key text,
    created_at timestamptz not null default now()
);

create unique index if not exists income_user_external_key_uq
on public.income(user_id, external_key)
where external_key is not null;

create table if not exists public.fixed_income_movements (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    movement_date date not null,
    direction text,
    movement text not null,
    product text not null,
    institution text,
    quantity numeric(20,8) default 0,
    unit_price numeric(20,8) default 0,
    operation_value numeric(20,2) default 0,
    external_key text,
    source text default 'B3',
    created_at timestamptz not null default now()
);

create unique index if not exists fixed_income_user_external_key_uq
on public.fixed_income_movements(user_id, external_key)
where external_key is not null;

create table if not exists public.goals (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    target_value numeric(20,2) not null,
    target_date date,
    monthly_contribution numeric(20,2) default 0,
    assumed_annual_return numeric(10,4) default 0,
    created_at timestamptz not null default now()
);

-- RLS
alter table public.positions_base enable row level security;
alter table public.portfolio_meta enable row level security;
alter table public.operations enable row level security;
alter table public.income enable row level security;
alter table public.fixed_income_movements enable row level security;
alter table public.goals enable row level security;

-- Policies: cada usuário só vê e altera suas próprias linhas.
do $$
declare
    t text;
begin
    foreach t in array array[
        'positions_base',
        'portfolio_meta',
        'operations',
        'income',
        'fixed_income_movements',
        'goals'
    ]
    loop
        execute format('drop policy if exists "%s_select_own" on public.%I', t, t);
        execute format('drop policy if exists "%s_insert_own" on public.%I', t, t);
        execute format('drop policy if exists "%s_update_own" on public.%I', t, t);
        execute format('drop policy if exists "%s_delete_own" on public.%I', t, t);

        execute format(
            'create policy "%s_select_own" on public.%I for select using (auth.uid() = user_id)',
            t, t
        );
        execute format(
            'create policy "%s_insert_own" on public.%I for insert with check (auth.uid() = user_id)',
            t, t
        );
        execute format(
            'create policy "%s_update_own" on public.%I for update using (auth.uid() = user_id) with check (auth.uid() = user_id)',
            t, t
        );
        execute format(
            'create policy "%s_delete_own" on public.%I for delete using (auth.uid() = user_id)',
            t, t
        );
    end loop;
end $$;
