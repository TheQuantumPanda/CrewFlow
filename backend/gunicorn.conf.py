"""Gunicorn settings.

Tuned for a small container on a managed host (Render/Railway free tiers give
roughly 0.5 vCPU and 512 MB), not for a big machine.
"""
import multiprocessing
import os

# Two workers fit comfortably in 512 MB. The usual (2 * cores + 1) formula
# would start 5+ workers on a shared vCPU and spend the memory on nothing.
workers = int(os.environ.get("WEB_CONCURRENCY", min(2, multiprocessing.cpu_count() + 1)))

# Threads absorb the I/O wait on database round trips without the memory cost
# of another process.
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_class = "gthread"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", 60))
graceful_timeout = 30

# Slightly above a typical 60s load-balancer idle timeout, so the proxy is
# never the one holding a connection the worker has already closed.
keepalive = 65

# Recycle workers periodically; it caps the blast radius of a slow leak in any
# dependency without anyone having to notice one first.
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%({x-forwarded-for}i)s "%(r)s" %(s)s %(b)s %(M)sms'

preload_app = False  # each worker opens its own DB connections after forking
