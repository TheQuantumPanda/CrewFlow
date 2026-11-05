# CrewFlow production runtime

Architecture: React 18 + Vite 6.4.5 builds into `web/dist`; Flask 3.1.3 serves that SPA and `/api` on one origin. Gunicorn 26.2.0 uses gthread workers. React Router 7.18.5 remains declarative BrowserRouter. Production persistence is PostgreSQL; no separate frontend host, Redis or authentication service is required.

## Reviewed build

The existing multistage Dockerfile targets **linux/amd64**, Node 24.21.0 at build time and Python 3.12.16 on Debian 13 trixie at runtime. The Python base is digest-pinned. Record the resolved Node/build frontend/base identities from each build; moving tags, APT repositories and transitive Python resolution mean bit-for-bit reproducibility has not been established.

The Python base contains APT 3.0.3. Before any APT network operation, the Dockerfile downloads the reviewed APT and libapt 3.0.4 Debian archives using Python HTTPS, verifies each pinned SHA-256, and installs both with `dpkg`. Only then does APT use official HTTPS trixie/security sources to install the pinned runtime libraries. Do not move `apt update`/ordinary package installation before that bootstrap, mix Debian suites, or assume upgrading APT after a vulnerable download repairs earlier build exposure.

Psycopg-C **3.3.8** replaces a binary wheel whose private libpq/OpenSSL copies lagged vendor fixes. The native builder needs GCC, Python headers, libpq development headers and `pg_config`. Its isolated build tools are setuptools 83.0.0, wheel 0.48.0 and packaging 26.3. The source archive requires that setuptools version. Its disclosed Windows legacy-wheel advisory does not describe this Linux source-build operation; the tool is absent from the final runtime. Do not substitute `psycopg-binary`.

The C wheel is built separately and installed into the runtime through a read-only BuildKit mount. The runtime contains system libpq **17.11** and Debian OpenSSL **3.5.7-1~deb13u3**, no compiler or build-only dependencies, pip 26.3, non-root UID 10001, an exec-form Gunicorn startup and `AUTO_BOOTSTRAP=0`. An inactive ensurepip pip 25.0.1 wheel remains disclosed and owner-pending; do not use it to bootstrap environments. Node and frontend development packages are excluded from the final stage.

Verify inside a candidate image, without initializing an application/database:

```bash
python -c 'import psycopg; assert psycopg.pq.__impl__ == "c"; print(psycopg.__version__, psycopg.pq.version())'
python -m pip check
python -m pip list --format=json
dpkg-query -W
```

Psycopg's libpq version alone does not establish which OpenSSL is loaded. Retain native-library paths/loader evidence and Debian inventory along with scan results. Frontend output must retain 15 same-origin WOFF2 assets, SVG/favicon and complete third-party notices; no production source maps or inline data font faces. Keep `font-src 'self'` unchanged.

## Provider-neutral configuration

| Setting | Required production treatment |
| --- | --- |
| `APP_ENV` | `production`; verify health reports production, never silently fall back |
| `SECRET_KEY` | Stable private random signing key; rotation invalidates existing signed sessions |
| `DATABASE_URL` | Explicit restricted runtime PostgreSQL URL; verify database identity and TLS trust before writes |
| `AUTO_BOOTSTRAP` | `0` for every ordinary worker |
| `BOOTSTRAP_ADMIN_PASSWORD` | Private explicit value for separate first-admin provisioning only; omit from ordinary workers |
| `BOOTSTRAP_ADMIN_USERNAME` | Private provisioning choice; no published demo credentials |
| `PORT` | Container ingress binding, default 8000 in Docker startup |
| `WEB_CONCURRENCY`, `GUNICORN_THREADS` | Fit memory and database connection budget; default two workers/four threads |
| `FORWARDED_ALLOW_IPS` | Exact trusted ingress peer(s), finalized for actual host; never `*` |
| `SESSION_LIFETIME_SECONDS`, `ADMIN_IDLE_MINUTES` | Existing session/console policy; review operational needs |

HTTPS terminates at a trusted reverse proxy. Production session cookies are Secure, HttpOnly and SameSite=Lax; CSRF uses the existing cookie/header pairing. Do not disable either for ingress troubleshooting. Gunicorn scheme trust does not automatically establish trustworthy client-IP attribution. No wildcard CORS or speculative ProxyFix is needed for the single-origin architecture.

Local production HTTPS, cookie, CSRF, proxy-spoofing and browser tests passed in isolated infrastructure. This does not verify a future hosting provider. Test its actual trust boundary, hostname/Host behavior, redirects, HSTS, CSP, API `Cache-Control: no-store`, asset delivery and connection recovery before launch. `/api/healthz` is liveness; `/api/readyz` requires an actual reachable database and must not be mistaken for schema/migration validation.

## Controlled database preparation

Every operation below requires an explicitly approved target and write window. These instructions do not authorize execution.

1. Verify host/database identity, access controls, TLS verification, recovery plan and a usable backup. Never reuse local superuser credentials for application workers.
2. A setup administrator creates a non-superuser migrator and runtime role with no CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS or cross-role memberships. Revoke inappropriate PUBLIC database/schema/type privileges **only in the approved target**.
3. Give the migrator CONNECT and ownership/schema CREATE needed by the existing migrations. With its private configuration, `APP_ENV=production`, stable private key and `AUTO_BOOTSTRAP=0`, run from `backend/`:

   ```bash
   python -m flask --app task_management db upgrade
   python -m flask --app task_management db current
   ```

   Expected current head: `b7c1e2d4a9f0`. Do not run migrations from every worker. Do not run `init-db`, `seed` or downgrade against preserved data.
4. Apply reviewed grants for newly created objects. Runtime needs schema USAGE; users/employees/tasks SELECT INSERT UPDATE; departments SELECT INSERT; task_assignments SELECT INSERT UPDATE DELETE; activity_logs SELECT INSERT only. ID sequences need USAGE, and the three application enums need USAGE. No runtime DDL, table ownership, TRUNCATE, audit-history UPDATE/DELETE, migration-table read or membership in migrator/admin roles. Review future migrations and grants together.
5. Once, using a private explicit `BOOTSTRAP_ADMIN_PASSWORD`, run `python -m flask --app task_management create-admin` with the runtime permissions. This inserts baseline departments and the initial Super Admin if absent; it does not replace approved migrations. The command does not disclose passwords. Never use generated/logged/demo passwords. Remove provisioning secrets from normal worker configuration.
6. Start Gunicorn with runtime credentials and `AUTO_BOOTSTRAP=0`. Check readiness, migration revision through the appropriate controlled account, role denials, authenticated flows and audit policy.

Separate migrator ownership and restricted runtime grants have passed local PostgreSQL tests. Hosted role/provider constraints, certificate verification, pool budgets, failover, backups/retention and restore/rollback remain host-specific gates. SQLAlchemy uses pre-ping/recycle; account for each worker's pool/overflow against provider limits and review transaction-pooler compatibility separately.

See [release assurance](release-assurance.md), [verification](VERIFICATION.md), and the [owner-pending security register](security-decisions.json). No public release is cleared by this document.
