create extension if not exists pgcrypto;

create table if not exists public.chat_threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  parent_thread_id uuid references public.chat_threads(id) on delete cascade,
  context_type text not null default 'recommendation'
    check (context_type in ('recommendation', 'movie')),
  context_movie_id bigint,
  context_movie jsonb,
  title text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references public.chat_threads(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  parent_message_id uuid references public.chat_messages(id) on delete set null,
  role text not null check (role in ('user', 'assistant')),
  content text not null check (char_length(content) between 1 and 4000),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists chat_threads_user_updated_idx
  on public.chat_threads (user_id, updated_at desc);
create index if not exists chat_threads_parent_idx
  on public.chat_threads (parent_thread_id);
create index if not exists chat_messages_thread_created_idx
  on public.chat_messages (thread_id, created_at);
create index if not exists chat_messages_user_idx
  on public.chat_messages (user_id);

alter table public.chat_threads enable row level security;
alter table public.chat_messages enable row level security;

create policy "Users can read their own chat threads"
  on public.chat_threads for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "Users can create their own chat threads"
  on public.chat_threads for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "Users can update their own chat threads"
  on public.chat_threads for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Users can delete their own chat threads"
  on public.chat_threads for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy "Users can read their own chat messages"
  on public.chat_messages for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "Users can create their own chat messages"
  on public.chat_messages for insert to authenticated
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.chat_threads
      where chat_threads.id = thread_id
      and chat_threads.user_id = (select auth.uid())
    )
  );

create policy "Users can update their own chat messages"
  on public.chat_messages for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Users can delete their own chat messages"
  on public.chat_messages for delete to authenticated
  using ((select auth.uid()) = user_id);
