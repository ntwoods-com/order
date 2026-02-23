# Sale Order API + Reports Download (Supabase Storage)

This repo serves a Flask API (`/api/v1/*`) and a React frontend (`frontend/`).

---

## Render Deployment (Backend)

### Start Command

```
gunicorn wsgi:app -c gunicorn.conf.py
```

### Build Command

```
pip install -r requirements.txt
```

### Environment Variables (set in Render Dashboard)

| Variable | Required | Example |
|---|---|---|
| `SECRET_KEY` | ✅ | `some-random-secret-string` |
| `DATABASE_URL` | ✅ | `postgresql://user:pass@host:5432/dbname` |
| `APP_ENV` | ✅ | `production` |
| `SUPABASE_URL` | ✅ | `https://<project>.supabase.co` |
| `SUPABASE_KEY` | ✅ | `<SERVICE_ROLE_KEY>` |
| `SUPABASE_STORAGE_BUCKET` | ✅ | `sale-orders` |
| `SESSION_COOKIE_SECURE` | Optional | `1` (default in production) |
| `USER1` | ✅ | `admin:$2b$12$...bcrypt_hash` |
| `CORS_ALLOWED_ORIGINS` | Optional | `https://your-frontend.com` |

> **Note:** If your `DATABASE_URL` uses Supabase, make sure the Supabase project is **not paused** (free tier pauses after 1 week of inactivity). Go to your Supabase dashboard and resume the project if needed.

---

## Supabase Storage configuration (backend only)

Reports and uploads can be stored either locally (default) or in Supabase Storage.

Set these env vars on the **backend**:

- `SUPABASE_URL=https://<project>.supabase.co`
- `SUPABASE_KEY=<SERVICE_ROLE_KEY>` (recommended) or `SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>`
  - Do **not** expose the Service Role key in the frontend.
- `SUPABASE_STORAGE_BUCKET=sale-orders` (or your bucket name)

On startup, the backend logs:

- bucket name
- detected key role (`service_role` vs `anon` vs `unknown`)

This helps debug downloads without printing secrets.

## Verification steps (reports download)

1) Upload or place a report object in your bucket at:

- `reports/<report_name>`

2) Call the backend download endpoint:

- `GET /api/v1/reports/<report_name>`

Expected behavior:

- `200` + file download when allowed
- `403` when Storage policies/key do not allow access (permission issue)
- `404` only when the object is truly missing (wrong name/path or not uploaded)
