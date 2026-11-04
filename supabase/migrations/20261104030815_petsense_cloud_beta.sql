-- Cloud beta uses Supabase Auth identities; no legacy SQLite data is imported.
create schema if not exists petsense_private;
revoke all on schema petsense_private from public, anon;
grant usage on schema petsense_private to authenticated;

create or replace function petsense_private.session_active() returns boolean
language sql stable security definer set search_path = '' as $$
  select auth.uid() is not null
    and coalesce(auth.jwt()->>'is_anonymous', 'false') = 'false'
    and exists(select 1 from auth.sessions s
      where s.id = nullif(auth.jwt()->>'session_id','')::uuid
        and s.user_id = auth.uid() and (s.not_after is null or s.not_after > now()));
$$;
revoke all on function petsense_private.session_active() from public, anon;
grant execute on function petsense_private.session_active() to authenticated;

create or replace function public.ps_session_active() returns boolean
language sql stable security invoker set search_path = '' as $$
  select petsense_private.session_active();
$$;
revoke all on function public.ps_session_active() from public, anon;
grant execute on function public.ps_session_active() to authenticated;

create table public.ps_accounts (
 id uuid primary key default auth.uid() references auth.users(id) on delete cascade,
 created_at timestamptz not null default now(),
 accept_terms boolean not null check(accept_terms),
 accept_privacy boolean not null check(accept_privacy),
 terms_version text not null check(terms_version='2026-11-04'),
 privacy_version text not null check(privacy_version='2026-11-04')
);
create table public.ps_dogs (
 id uuid primary key default gen_random_uuid(),
 owner uuid not null default auth.uid() references public.ps_accounts(id) on delete cascade,
 name text not null check(length(btrim(name)) between 1 and 40),
 species text not null default 'dog' check(species='dog'),
 breed text check(breed is null or length(breed)<=80),
 age_months integer check(age_months is null or age_months between 0 and 360),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 expires_at timestamptz not null default now()+interval '30 days',
 unique(id,owner)
);
create table public.ps_notes (
 id uuid primary key default gen_random_uuid(),
 owner uuid not null default auth.uid() references public.ps_accounts(id) on delete cascade,
 pet_id uuid not null,
 observation text not null check(length(btrim(observation)) between 1 and 2000),
 followup text not null default '' check(length(followup)<=2000),
 origin text not null default 'guardian_report' check(origin='guardian_report'),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 expires_at timestamptz not null default now()+interval '30 days',
 foreign key(pet_id,owner) references public.ps_dogs(id,owner) on delete cascade
);
create table public.ps_requests (
 id uuid primary key default gen_random_uuid(),
 owner uuid not null default auth.uid() references public.ps_accounts(id) on delete cascade,
 pet_id uuid not null,
 context text not null check(length(btrim(context)) between 1 and 2000),
 status text not null default 'awaiting_model' check(status in ('awaiting_model','cancelled')),
 request_kind text not null default 'guardian_context' check(request_kind='guardian_context'),
 consent_version text not null check(consent_version='2026-11-04'),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 expires_at timestamptz not null default now()+interval '30 days',
 foreign key(pet_id,owner) references public.ps_dogs(id,owner) on delete cascade
);
create table public.ps_plans (
 id uuid primary key default gen_random_uuid(),
 owner uuid not null default auth.uid() references public.ps_accounts(id) on delete cascade,
 pet_id uuid not null,
 title text not null check(length(btrim(title)) between 1 and 100),
 detail text not null default '' check(length(detail)<=2000),
 completed boolean not null default false,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 expires_at timestamptz not null default now()+interval '30 days',
 foreign key(pet_id,owner) references public.ps_dogs(id,owner) on delete cascade
);

alter table public.ps_accounts enable row level security;
create policy account_read on public.ps_accounts for select to authenticated
 using(id=(select auth.uid()) and (select petsense_private.session_active()));
create policy account_create on public.ps_accounts for insert to authenticated
 with check(id=(select auth.uid()) and (select petsense_private.session_active()));
revoke all on public.ps_accounts from anon,authenticated;
grant select on public.ps_accounts to authenticated;
grant insert(accept_terms,accept_privacy,terms_version,privacy_version) on public.ps_accounts to authenticated;

create function petsense_private.guard_beta_write() returns trigger
language plpgsql security invoker set search_path = '' as $$
declare quota integer;
begin
 if not petsense_private.session_active() then raise exception 'Active non-anonymous session required'; end if;
 perform pg_advisory_xact_lock(hashtextextended(new.owner::text,0));
 if tg_op='INSERT' then
  new.created_at=now(); new.updated_at=now(); new.expires_at=now()+interval '30 days';
  if tg_table_name='ps_dogs' then
   select count(*) into quota from public.ps_dogs where owner=new.owner and expires_at>now();
   if quota>=20 then raise exception 'Dog quota exceeded'; end if;
  elsif tg_table_name='ps_notes' then
   select count(*) into quota from public.ps_notes where owner=new.owner and expires_at>now();
   if quota>=500 then raise exception 'Note quota exceeded'; end if;
  elsif tg_table_name='ps_requests' then
   select count(*) into quota from public.ps_requests where owner=new.owner and created_at>now()-interval '24 hours';
   if quota>=20 then raise exception 'Daily request quota exceeded'; end if;
  elsif tg_table_name='ps_plans' then
   select count(*) into quota from public.ps_plans where owner=new.owner and expires_at>now();
   if quota>=100 then raise exception 'Plan quota exceeded'; end if;
  end if;
 else
  if new.owner is distinct from old.owner or new.id is distinct from old.id or new.created_at is distinct from old.created_at or new.expires_at is distinct from old.expires_at then
   raise exception 'Ownership and retention are immutable';
  end if;
  new.updated_at=now();
  if tg_table_name='ps_requests' and new.status<>'cancelled' then raise exception 'Only cancellation is available'; end if;
 end if;
 return new;
end;
$$;
revoke all on function petsense_private.guard_beta_write() from public,anon,authenticated;

-- Policy ownership and composite foreign keys also prevent referencing another dog's owner.
do $$ declare t text; begin
 foreach t in array array['ps_dogs','ps_notes','ps_requests','ps_plans'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('revoke all on public.%I from anon,authenticated',t);
  execute format('grant select,delete on public.%I to authenticated',t);
  execute format('create policy owner_read on public.%I for select to authenticated using (owner=(select auth.uid()) and expires_at>now() and (select petsense_private.session_active()))',t);
  execute format('create policy owner_delete on public.%I for delete to authenticated using (owner=(select auth.uid()) and (select petsense_private.session_active()))',t);
  execute format('create policy owner_insert on public.%I for insert to authenticated with check (owner=(select auth.uid()) and expires_at<=now()+interval ''30 days'' and (select petsense_private.session_active()))',t);
  execute format('create policy owner_update on public.%I for update to authenticated using (owner=(select auth.uid()) and expires_at>now() and (select petsense_private.session_active())) with check (owner=(select auth.uid()) and expires_at<=now()+interval ''30 days'' and (select petsense_private.session_active()))',t);
  execute format('create trigger guard_write before insert or update on public.%I for each row execute function petsense_private.guard_beta_write()',t);
  execute format('create index %I on public.%I(owner,created_at desc)',t||'_owner_created',t);
 end loop;
end $$;
grant insert(name,species,breed,age_months) on public.ps_dogs to authenticated;
grant update(name,breed,age_months) on public.ps_dogs to authenticated;
grant insert(pet_id,observation,followup) on public.ps_notes to authenticated;
grant update(observation,followup) on public.ps_notes to authenticated;
grant insert(id,pet_id,context,consent_version) on public.ps_requests to authenticated;
grant update(status) on public.ps_requests to authenticated;
grant insert(pet_id,title,detail) on public.ps_plans to authenticated;
grant update(title,detail,completed) on public.ps_plans to authenticated;

comment on table public.ps_requests is 'Text-only observation requests. No worker connected, no inference or fabricated completion.';
