# SEDO Year 3 Library Web App

Secure Flask web application for managing an organisation's professional development library.

## Stack

- Flask
- Supabase Python client/API
- Supabase Auth JWT sessions
- Supabase Row Level Security policies
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

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `FLASK_ENV=production`

Use the Supabase anon/publishable key for `SUPABASE_ANON_KEY`. Use the service role key only for `SUPABASE_SERVICE_ROLE_KEY`; it is required for creating/deleting Supabase Auth users and must never be exposed in browser code or committed to GitHub.

## Supabase Setup

1. Open the Supabase SQL editor.
2. Run the SQL files in `supabase/migrations` in order.
3. Add `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` to `.env` locally and to Render.
4. Run `python -m flask --app run.py seed-db` locally once to create confirmed Supabase Auth users, linked app profiles, and sample books.

The app uses Flask for page routing and user experience checks, while Supabase Auth issues JWTs and Supabase RLS enforces database-level access control. The schema uses `users`, `books`, and `loans` so current book status and borrowing history can both be evidenced. Usernames are mapped to internal Supabase Auth emails using the pattern `username@sedo-library.local`, keeping the visible login form username-based.

## CI/CD

GitHub Actions runs:

- `pytest` for automated functional/security behaviour tests.
- `bandit -r app -x tests` for static security scanning.
- Render deployment hook on successful pushes to `main` when the `RENDER_DEPLOY_HOOK_URL` secret is configured.

## Tests

```bash
pytest
```
