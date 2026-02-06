# Sale Order API + Reports Download (Supabase Storage)

This repo serves a Flask API (`/api/v1/*`) and a React frontend (`frontend/`).

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

