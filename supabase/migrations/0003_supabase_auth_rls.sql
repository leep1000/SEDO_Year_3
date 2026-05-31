alter table public.users
    add column if not exists auth_user_id uuid unique references auth.users(id) on delete cascade;

alter table public.users
    drop column if exists password_hash;

create index if not exists ix_users_auth_user_id on public.users(auth_user_id);

create or replace function public.current_app_user_id()
returns integer
language sql
stable
security definer
set search_path = public
as $$
    select id
    from public.users
    where auth_user_id = auth.uid()
    limit 1
$$;

create or replace function public.current_app_user_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
    select role
    from public.users
    where auth_user_id = auth.uid()
    limit 1
$$;

create or replace function public.current_app_user_is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select coalesce(public.current_app_user_role() = 'admin', false)
$$;

grant usage on schema public to authenticated;
grant select, insert, update, delete on table public.users to authenticated;
grant select, insert, update, delete on table public.books to authenticated;
grant select, insert, update, delete on table public.loans to authenticated;
grant usage, select on all sequences in schema public to authenticated;
grant execute on function public.current_app_user_id() to authenticated;
grant execute on function public.current_app_user_role() to authenticated;
grant execute on function public.current_app_user_is_admin() to authenticated;

alter table public.users enable row level security;
alter table public.books enable row level security;
alter table public.loans enable row level security;

drop policy if exists users_select_own_or_admin on public.users;
drop policy if exists users_insert_own_regular_profile on public.users;
drop policy if exists users_admin_update on public.users;
drop policy if exists users_delete_own_or_admin on public.users;

create policy users_select_own_or_admin
on public.users
for select
to authenticated
using (auth_user_id = auth.uid() or public.current_app_user_is_admin());

create policy users_insert_own_regular_profile
on public.users
for insert
to authenticated
with check (auth_user_id = auth.uid() and role = 'regular');

create policy users_admin_update
on public.users
for update
to authenticated
using (public.current_app_user_is_admin())
with check (public.current_app_user_is_admin());

create policy users_delete_own_or_admin
on public.users
for delete
to authenticated
using (auth_user_id = auth.uid() or public.current_app_user_is_admin());

drop policy if exists books_select_authenticated on public.books;
drop policy if exists books_insert_own on public.books;
drop policy if exists books_update_admin on public.books;
drop policy if exists books_update_user_checkout_return on public.books;
drop policy if exists books_delete_own_or_admin on public.books;

create policy books_select_authenticated
on public.books
for select
to authenticated
using (true);

create policy books_insert_own
on public.books
for insert
to authenticated
with check (created_by_id = public.current_app_user_id());

create policy books_update_admin
on public.books
for update
to authenticated
using (public.current_app_user_is_admin())
with check (public.current_app_user_is_admin());

create policy books_update_user_checkout_return
on public.books
for update
to authenticated
using (
    status = 'available'
    or checked_out_by_id = public.current_app_user_id()
    or created_by_id = public.current_app_user_id()
)
with check (
    checked_out_by_id is null
    or checked_out_by_id = public.current_app_user_id()
    or created_by_id = public.current_app_user_id()
);

create policy books_delete_own_or_admin
on public.books
for delete
to authenticated
using (created_by_id = public.current_app_user_id() or public.current_app_user_is_admin());

drop policy if exists loans_select_own_or_admin on public.loans;
drop policy if exists loans_insert_own on public.loans;
drop policy if exists loans_update_own_or_admin on public.loans;

create policy loans_select_own_or_admin
on public.loans
for select
to authenticated
using (
    user_id = public.current_app_user_id()
    or actioned_by_id = public.current_app_user_id()
    or public.current_app_user_is_admin()
);

create policy loans_insert_own
on public.loans
for insert
to authenticated
with check (
    (
        user_id = public.current_app_user_id()
        and actioned_by_id = public.current_app_user_id()
    )
    or public.current_app_user_is_admin()
);

create policy loans_update_own_or_admin
on public.loans
for update
to authenticated
using (user_id = public.current_app_user_id() or public.current_app_user_is_admin())
with check (user_id = public.current_app_user_id() or public.current_app_user_is_admin());
