# Sale Order System (Backend + Frontend)

- Backend: Flask (deploy to Render)
- Frontend: React (deploy to GitHub Pages)

## Backend (local)

1. Install deps:
   - `python -m venv .venv`
   - `.venv\\Scripts\\Activate.ps1`
   - `pip install -r requirements.txt`
2. Create `.env` (local dev only):
   - Copy `.env.example` -> `.env`
3. Run:
   - `python app.py`

## Frontend (local)

1. `cd frontend`
2. `npm install`
3. Create `frontend/.env`:
   - Copy `frontend/.env.example` -> `frontend/.env`
   - Set `VITE_API_BASE_URL=http://localhost:5000`
4. Run:
   - `npm run dev`

## Deploy backend (Render)

This repo includes `render.yaml` (Blueprint).

Required env vars (Render dashboard -> Environment):
- `SECRET_KEY` (long random string)
- `JWT_SECRET` (can be same as `SECRET_KEY`)
- `USER1`, `USER2`, ... in format `username:bcrypt_hash`
- `ADMIN_USERS` (comma-separated usernames, e.g. `admin`)
- `DATABASE_URL` (recommended for production; Render disk is not a reliable DB)

Optional:
- `CORS_ALLOWED_ORIGINS` (comma-separated) e.g. `https://<username>.github.io`
- `JWT_EXPIRES_SECONDS` (default 28800)

Health check path: `/api/v1/health`

## Deploy frontend (GitHub Pages)

This repo includes a workflow: `.github/workflows/deploy-frontend.yml`.

1. In GitHub repo settings:
   - Settings -> Pages -> Source: **GitHub Actions**
2. Set Actions variable:
   - Settings -> Secrets and variables -> Actions -> Variables
   - `VITE_API_BASE_URL` = your Render backend URL (example: `https://your-app.onrender.com`)
3. Push to `main` -> workflow builds `frontend/` and deploys Pages.

Note: Frontend uses `HashRouter` so refresh/direct links work on GitHub Pages.

## Render "server sleep" issue (Free plan)

Render **Free** web services can spin down when idle. That behavior cannot be fully removed by code.

Options:
1. Upgrade the Render service plan (always-on).
2. If you must stay on Free, use an external uptime monitor (e.g. UptimeRobot) to hit `/api/v1/health` every ~5 minutes (workaround; cold starts can still happen).

## Tools

- Generate bcrypt hash:
  - `python tools/gen_bcrypt_hash.py --env-key USER1 --username admin`
  - `python tools/gen_bcrypt_hash.py --env-key USER2 --username user2`
- Seed demo data (optional):
  - `python tools/seed_demo_data.py --rows 200`

