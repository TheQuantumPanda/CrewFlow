<div align="center">

# 🚀 Deployment

**[← Back to README](README.md)** · [Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY.md) · [API](docs/API.md) · [Development](docs/DEVELOPMENT.md) · [Screenshots](docs/SCREENSHOTS.md)

</div>

---

The app ships as a single container: Node builds the React bundle, then a slim
Python image serves both that bundle and the API through Gunicorn. Any host
that can run a Dockerfile can run it.

---

## Why the previous Railway deploy stopped working

The old URL returns `{"status":"error","code":404,"message":"Application not found"}`.
That is Railway's edge saying **the service no longer exists** — it is not a
build failure or a crash loop. Railway's trial credit expires and the project
is removed with it. Redeploying the old configuration would not have helped,
because nothing was left to redeploy into.

Two things in the old setup would also have broken a fresh deploy:

1. **Postgres was unsupported.** `config.py` only rewrote `mysql://`. Railway
   and Render both hand out `postgres://`, which SQLAlchemy 2 rejects outright
   (`Can't load plugin: sqlalchemy.dialects:postgres`) — a crash at boot, before
   the first request. That normalisation is now pinned by `test_config.py`.
2. **A fresh database had no departments.** Signup requires picking one, and
   the picker is populated from the database, so nobody could create the first
   account. First boot now seeds departments and an admin.

---

## Option 1 — Render (recommended)

Free web service, free managed Postgres, and `render.yaml` already describes
both.

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, select the repo.
3. Render reads `render.yaml`, creates the web service and the database, and
   wires `DATABASE_URL` between them. `SECRET_KEY` is generated once and held
   constant across deploys.
4. Open the deploy log and find the line beginning `BOOTSTRAP ADMIN CREATED` —
   it prints the generated admin password **once**. Sign in and change it.

To choose your own password instead, set `BOOTSTRAP_ADMIN_PASSWORD` in the
service's environment before the first deploy.

> **Free tier caveats.** The service sleeps after ~15 minutes idle, so the
> first request afterwards takes 30–60s. Render's free Postgres expires after
> 30 days — for a demo link that has to stay alive, point `DATABASE_URL` at a
> [Neon](https://neon.tech) free database instead, which does not expire, and
> delete the `databases:` block from `render.yaml`.

---

## Option 2 — Railway

1. **New Project → Deploy from GitHub repo.**
2. **New → Database → PostgreSQL.** Railway injects `DATABASE_URL` into the
   web service automatically.
3. Set these variables on the web service:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `APP_ENV` | `production` |
   | `BOOTSTRAP_ADMIN_PASSWORD` | your choice (optional) |

4. Deploy. `railway.toml` selects the Dockerfile and points the health check at
   `/api/healthz`.

---

## Option 3 — Fly.io

```bash
fly launch --no-deploy            # detects the Dockerfile
fly postgres create               # then: fly postgres attach <name>
fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" APP_ENV=production
fly deploy
```

Fly's free allowance does not expire, which makes it the best choice if the
demo link needs to stay up indefinitely.

---

## Option 4 — Any Docker host

```bash
docker build -t taskforge .

docker run -d -p 8000:8000 \
  -e APP_ENV=production \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e DATABASE_URL="postgresql://user:pass@host:5432/taskforge" \
  taskforge
```

---

## Environment variables

| Variable | Required | Default | Notes |
|---|:---:|---|---|
| `SECRET_KEY` | **in production** | — | The app refuses to boot without it. A rotating key signs every visitor out on each restart. |
| `APP_ENV` | | `development` | `production` turns on secure cookies and HSTS. |
| `DATABASE_URL` | | SQLite file | `postgres://`, `postgresql://` and `mysql://` are all normalised to the installed driver. |
| `BOOTSTRAP_ADMIN_USERNAME` | | `admin` | |
| `BOOTSTRAP_ADMIN_PASSWORD` | | random | Generated and logged once if unset. |
| `AUTO_BOOTSTRAP` | | `1` | Set `0` to manage the schema entirely by hand. |
| `WEB_CONCURRENCY` | | `2` | Gunicorn workers. |
| `MAX_FAILED_LOGINS` | | `5` | |
| `LOCKOUT_MINUTES` | | `15` | |
| `MIN_PASSWORD_LENGTH` | | `8` | |
| `PORT` | | `8000` | Injected by most hosts. |

Never set `DATABASE_URL` to a SQLite file on a host with an ephemeral
filesystem — every deploy would wipe the data.

---

## First boot

On an empty database the app:

1. applies Alembic migrations (or `create_all()` if `migrations/` is absent),
2. creates the five default departments,
3. creates one admin account and logs the password if it generated one.

Every step is idempotent, so it is safe on each restart and a no-op once the
database is populated.

---

## Health checks

| Endpoint | Purpose |
|---|---|
| `/api/healthz` | Liveness. Touches nothing, so it answers even when the database is down. |
| `/api/readyz` | Readiness. Round-trips `SELECT 1`; returns **503** if the database is unreachable. |

Point a platform health check at `/api/healthz`. Gating on `/readyz` would make
the platform kill and restart the container during a database blip, which does
not help and turns a brief outage into a restart loop.

---

## Troubleshooting

**`Can't load plugin: sqlalchemy.dialects:postgres`** — an old build without URL
normalisation. Fixed in `config.py`; confirm with `pytest tests/test_config.py`.

**`RuntimeError: SECRET_KEY must be set in production`** — working as intended.
Set it.

**Signup shows an empty department dropdown** — bootstrap did not run. Check the
boot log for `Bootstrap skipped — database not ready`, which means
`DATABASE_URL` is wrong or the database was not reachable at start.

**Everyone is signed out after each deploy** — `SECRET_KEY` is changing between
deploys. Set it once as a fixed secret.

**`/api/readyz` returns 503** — the app is up, the database is not. Check the
connection string, and whether the provider requires `?sslmode=require`.

**First request takes 30–60 seconds** — a free-tier container waking from
sleep. Not a bug.
