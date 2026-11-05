# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the React SPA.
# Node is only needed to produce static files, so it never reaches the runtime
# image. That keeps the deployed container to Python plus the built assets.
# ---------------------------------------------------------------------------
FROM node:24.21.0-bookworm-slim AS web

WORKDIR /web

# Copy the manifests first so `npm ci` is only re-run when dependencies
# actually change, not on every source edit.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 — the Python runtime.
# ---------------------------------------------------------------------------
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30 AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    AUTO_BOOTSTRAP=0

WORKDIR /app

# Bootstrap the reviewed amd64 APT fix without asking vulnerable APT to fetch
# packages. Hashes come from signed Debian trixie-security package metadata.
RUN python - <<'PY'
import hashlib
import pathlib
import subprocess
import urllib.request

if subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip() != "amd64":
    raise SystemExit("This reviewed bootstrap targets linux/amd64")

packages = {
    "libapt-pkg7.0_3.0.4_amd64.deb": "577eb8f489de419290102364892dbd13ca256297b61f96d61b114fd4ac18be41",
    "apt_3.0.4_amd64.deb": "15c2030e0fb46580af4f1b4cc303f4bd26da781b004e99763bc9eff7cf8e19b8",
}
paths = []
for name, expected in packages.items():
    url = "https://security.debian.org/debian-security/pool/updates/main/a/apt/" + name
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise SystemExit("Debian bootstrap checksum mismatch")
    path = pathlib.Path("/tmp") / name
    path.write_bytes(payload)
    paths.append(path)
subprocess.run(["dpkg", "-i", *map(str, paths)], check=True)
for package in ("apt", "libapt-pkg7.0"):
    version = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", package], text=True)
    if version != "3.0.4":
        raise SystemExit("Unexpected APT bootstrap version")
for path in paths:
    path.unlink()
sources = pathlib.Path("/etc/apt/sources.list.d/debian.sources")
sources.write_text(sources.read_text().replace("http://deb.debian.org/", "https://deb.debian.org/"))
PY

# System libpq/OpenSSL are maintained by Debian; curl backs HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5=17.11-0+deb13u1 curl=8.14.1-2+deb13u7 \
    && rm -rf /var/lib/apt/lists/*

# Bootstrap only the reviewed PyPI wheel; verify its published SHA-256 before
# using the patched installer for application dependencies.
RUN python -m pip --isolated install --no-cache-dir --no-deps \
    "https://files.pythonhosted.org/packages/07/25/ee8c38ae72d66b844ce8eb9711ba905dba21ca1a8a0c960057c41cd23337/pip-26.3-py3-none-any.whl#sha256=f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13"

# Compile only the driver in a disposable build stage. No compiler, headers,
# setuptools or wheel build tools are copied to the production runtime.
FROM python-base AS native-builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc=4:14.2.0-1 libc6-dev=2.41-12+deb13u4 libpq-dev=17.11-0+deb13u1 \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip --isolated install --no-cache-dir --no-deps \
    "https://files.pythonhosted.org/packages/5d/40/e1e72872c6354b306daef1703549e8e83b4d43cfea356311bf722a043752/setuptools-83.0.0-py3-none-any.whl#sha256=29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3" \
    "https://files.pythonhosted.org/packages/2e/29/69cfbb602cd91690c55d38ba9fe53e6a7e76a6fa647bf38f19c138d25449/wheel-0.48.0-py3-none-any.whl#sha256=3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab" \
    "https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl#sha256=d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c"
RUN python -m pip --isolated wheel --no-cache-dir --no-deps --no-build-isolation \
    --wheel-dir /wheels \
    "https://files.pythonhosted.org/packages/5b/23/0074f50899d773aae857af496745cd898da868f8f2d9415591d51c391cec/psycopg_c-3.3.8.tar.gz#sha256=af81a99b02600e6c2cdf468509c04bb8208500ea60d63f70616e32ea9cb2758f"

FROM python-base AS runtime
# Fail rather than silently falling back to another driver implementation.
ENV PSYCOPG_IMPL=c
COPY backend/requirements.txt ./backend/requirements.txt
RUN --mount=type=bind,from=native-builder,source=/wheels,target=/wheels,readonly \
    python -m pip --isolated install --no-cache-dir \
    --index-url https://pypi.org/simple --find-links=/wheels \
    --only-binary=psycopg-c -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=web /web/dist ./web/dist
COPY LICENSE ./LICENSE

# Run as an unprivileged user — a process that never needs to write to the
# image should not be able to.
RUN useradd --create-home --uid 10001 taskforge \
    && chown -R taskforge:taskforge /app
USER taskforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/healthz" || exit 1

# Expand the injected port, then replace the shell so Gunicorn receives SIGTERM.
CMD ["sh", "-c", "exec gunicorn --chdir backend --config backend/gunicorn.conf.py --bind 0.0.0.0:${PORT:-8000} 'task_management:create_app()'"]
