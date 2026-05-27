# SEDO Year 3 Library Web App

Secure Flask web application for managing an organisation's professional development library.

## Stack

- Flask
- SQLAlchemy
- Supabase hosted PostgreSQL
- Render web service
- GitHub Actions CI/CD
- pytest automated tests

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m flask --app run.py seed-db
python run.py
```

Open `http://localhost:5000`.

## Default Seed Users

- Admin: `adminuser` / `AdminPass123!`
- Regular: `regularuser` / `RegularPass123!`

Change these values before deployment using environment variables.

## Deployment

The app is designed for Render with a Supabase PostgreSQL database.

Required Render environment variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `FLASK_ENV=production`

Use the Supabase pooler connection string for `DATABASE_URL` and replace the `postgres://` prefix with `postgresql://` if needed.

## Supabase Setup

1. Open the Supabase SQL editor.
2. Run `supabase/migrations/0001_initial_schema.sql`.
3. Add the Supabase connection string to `.env` locally and to Render as `DATABASE_URL`.
4. Run `python -m flask --app run.py seed-db` locally against Supabase once to create the admin user and sample books with hashed passwords.

The app uses Flask/SQLAlchemy for application access control. Supabase is used as the central PostgreSQL database so all users interact with the same data. The schema uses `users`, `books`, and `loans` so current book status and borrowing history can both be evidenced.

## CI/CD

GitHub Actions runs:

- `pytest` for automated functional/security behaviour tests.
- `bandit -r app -x tests` for static security scanning.
- Render deployment hook on successful pushes to `main` when the `RENDER_DEPLOY_HOOK_URL` secret is configured.

## Tests

```bash
pytest
```
