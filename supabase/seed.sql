insert into users (username, password_hash, role)
values
    ('adminuser', 'set-by-flask-seed-db-command', 'admin'),
    ('regularuser', 'set-by-flask-seed-db-command', 'regular')
on conflict (username) do nothing;

-- Use `python -m flask --app run.py seed-db` after configuring DATABASE_URL
-- so seeded users receive secure Werkzeug password hashes.

