-- Muisti online: Anki's tables as rows per user. Desktop (cloud.py) and web (ui/src/web) both write plain upserts;
-- the trigger below gives every write the next usn of its user and keeps the newer `mod` (Anki's own rule).
-- Desktop pulls `usn > last_usn and device <> me`; deletions are rows with deleted = true.

create table public.sync_state (
  user_id uuid primary key references auth.users on delete cascade,
  usn bigint not null default 0,
  schema int not null default 1  -- raise on breaking changes: older apps then ask for an update instead of syncing
);

create table public.notes (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  id bigint not null,
  guid text, mid bigint, mod bigint not null, usn bigint not null default 0,
  tags text, flds text, sfld text, csum bigint, flags int, data text,
  device text, deleted boolean not null default false,
  primary key (user_id, id)
);

create table public.cards (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  id bigint not null,
  nid bigint, did bigint, ord int, mod bigint not null, usn bigint not null default 0,
  type int, queue int, due bigint, ivl int, factor int, reps int, lapses int, "left" int,
  odue bigint, odid bigint, flags int, data text,
  device text, deleted boolean not null default false,
  primary key (user_id, id)
);

create table public.revlog (  -- insert only
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  id bigint not null,
  cid bigint not null, ease int, ivl int, last_ivl int, factor int, time int, type int,
  mod bigint not null default 0, usn bigint not null default 0,
  device text, deleted boolean not null default false,
  primary key (user_id, id)
);

-- decks, presets, note types, config: Anki's legacy JSON dicts (col.decks.get(), col.models.get(), ...)
create table public.decks (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  id bigint not null, mod bigint not null, usn bigint not null default 0, data jsonb,
  device text, deleted boolean not null default false,
  primary key (user_id, id)
);
create table public.deck_configs (like public.decks including all);
create table public.notetypes (like public.decks including all);
create table public.config (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  key text not null, mod bigint not null, usn bigint not null default 0, val jsonb,
  device text, deleted boolean not null default false,
  primary key (user_id, key)
);
alter table public.deck_configs add foreign key (user_id) references auth.users on delete cascade;
alter table public.notetypes add foreign key (user_id) references auth.users on delete cascade;

create function public.stamp() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'UPDATE' and new.mod < old.mod then
    return null;  -- an older change arrived late: keep the newer one
  end if;
  insert into public.sync_state (user_id, usn) values (new.user_id, 1)
    on conflict (user_id) do update set usn = public.sync_state.usn + 1
    returning usn into new.usn;  -- the per-user row lock orders commits, so `usn > x` never misses one
  return new;
end $$;
revoke execute on function public.stamp() from public, anon, authenticated;

do $$
declare t text;
begin
  foreach t in array array['notes', 'cards', 'revlog', 'decks', 'deck_configs', 'notetypes', 'config'] loop
    execute format('create trigger stamp before insert or update on public.%I for each row execute function public.stamp()', t);
    execute format('create index on public.%I (user_id, usn)', t);
    execute format('alter table public.%I enable row level security', t);
    execute format('create policy own on public.%I for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()))', t);
  end loop;
end $$;

create index on public.cards (user_id, did, queue, due);  -- the web's study queue
create index on public.cards (user_id, nid);
create index on public.revlog (user_id, cid);
-- ponytail: one table for all users; partition revlog by user_id hash once it reaches hundreds of millions of rows

alter table public.sync_state enable row level security;
create policy own on public.sync_state for select to authenticated using (user_id = (select auth.uid()));

-- media: private bucket, one folder per user
insert into storage.buckets (id, name, public) values ('media', 'media', false);
create policy own_media on storage.objects for all to authenticated
  using (bucket_id = 'media' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'media' and (storage.foldername(name))[1] = (select auth.uid())::text);
