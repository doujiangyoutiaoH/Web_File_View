Docker (quick start)
--------------------

This repository includes a `Dockerfile` and `docker-compose.yml` for running the app with Postgres.
Build and run with docker-compose:

```bash
docker-compose build
docker-compose up
```

The web app will be available at `http://localhost:8000`.
Notes:
- The Compose file mounts the current directory into the container for development convenience. For production remove the bind-mount.
- `DATABASE_URL` is set in `docker-compose.yml` to use the Postgres service. Alternatively, set `DATABASE_URL` to a SQLite file path or an external DB.
- Ensure `SECRET_KEY` and Azure settings are provided as environment variables in production.

# Backend README

Quick dev instructions:

1. Install dependencies and run the server:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Dev login (no Azure required) 鈥?for local testing only:

- Non-admin test user:

```
http://localhost:8000/dev_login
```

- Admin test user:

```
http://localhost:8000/dev_login?username=admin@example.com&admin=true
```

3. Production: register an app in Azure AD, set `redirect URI` to `http://<HOST>/auth/callback`, and set environment variables from `.env.example`.

Remove or disable `/dev_login` before deploying to production.

Server-side rendering and watermarking:

- This backend can render PDF pages server-side to PNG images and overlay per-user watermarks. The endpoint is:

  - `GET /files/{doc_id}/pages/{pageno}.png` 鈥?returns a watermarked PNG of page `pageno` for the authenticated user.

- Admins can set per-document allowed users:

  - `POST /admin/docs/{doc_id}/permissions` with form `allowed_users=alice@example.com,bob@contoso.com`.

  - `POST /admin/docs/{doc_id}/delete` to remove a document.
# Backend README

Quick dev instructions:

1. Install dependencies and run the server:

```bash
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Dev login (no Azure required) 鈥?for local testing only:

- Non-admin test user:

```
http://localhost:8000/dev_login
```

- Admin test user:

```
http://localhost:8000/dev_login?username=admin@example.com&admin=true
```

3. Production: register an app in Azure AD, set `redirect URI` to `http://<HOST>/auth/callback`, and set environment variables from `.env.example`.

Remove or disable `/dev_login` before deploying to production.

