# Sale Order System (Flask) — Render Ready

This repo contains a Flask app for generating and tracking sale orders (upload Excel → generate report → audit/history + dashboard + admin panel).

## Local setup

1. Install deps:
   - `python -m venv .venv`
   - `.venv\\Scripts\\Activate.ps1`
   - `pip install -r requirements.txt`
2. Create `.env` (for local dev only):
   - Copy `.env.example` → `.env`
   - Generate bcrypt hashes with: `python tools/gen_bcrypt_hash.py`
3. Run locally:
   - `python app.py`

## Production (Render)

### Required env vars (Render dashboard → Environment)
- `SECRET_KEY` (long random string)
- `JWT_SECRET` (can be same as `SECRET_KEY`)
- `USER1`, `USER2`, ... in format `username:bcrypt_hash`
- `ADMIN_USERS` (comma-separated usernames, e.g. `admin`)

### Database (important)
Render instances restart/redeploy and the filesystem is not a reliable database. For production you should use Postgres (e.g. Supabase) and set:
- `DATABASE_URL` (recommended)
  - If your Supabase URL uses `:6543` (transaction pooler), change it to `:5432` (session mode) for better stability.

### Deploy
- This repo includes `render.yaml` (Blueprint).
- Start command uses Gunicorn: `wsgi:application`.
- Health check path: `/api/v1/health`.

## Render “server sleep” issue (Free plan)

Render **Free** web services can spin down when idle. That behavior cannot be fully removed by code.

Options:
1. Upgrade the Render service plan (always-on).
2. If you must stay on Free, use an external uptime monitor (e.g. UptimeRobot) to hit `/api/v1/health` every ~5 minutes (this prevents idle spin-down but is still a workaround and you may still see cold starts after deploys).

## Tools

- Generate bcrypt hash:
  - `python tools/gen_bcrypt_hash.py --env-key USER1 --username admin`
  - `python tools/gen_bcrypt_hash.py --env-key USER2 --username user2`
- Seed demo data (optional):
  - `python tools/seed_demo_data.py --rows 200`
