"""Exercise the production server's config/parser without sockets or application boot."""
import runpy
from pathlib import Path

import pytest
from gunicorn.config import Config
from gunicorn.http.errors import ParseException
from gunicorn.http.message import Request
from gunicorn.http.unreader import IterUnreader


@pytest.fixture
def server_config(monkeypatch):
    for name in ["WEB_CONCURRENCY", "GUNICORN_THREADS", "GUNICORN_TIMEOUT", "FORWARDED_ALLOW_IPS"]:
        monkeypatch.delenv(name, raising=False)
    settings = runpy.run_path(str(Path(__file__).resolve().parents[1] / "gunicorn.conf.py"))
    cfg = Config()
    for key, value in settings.items():
        if key in cfg.settings:
            cfg.set(key, value)
    return cfg


def parse_request(cfg, headers, peer="127.0.0.1"):
    data = b"GET /api/healthz HTTP/1.1\r\n" + headers + b"\r\n"
    return Request(cfg, IterUnreader([data]), (peer, 12345))


def test_existing_gthread_configuration_and_trust_remain_restricted(server_config):
    assert server_config.worker_class.__module__ == "gunicorn.workers.gthread"
    assert server_config.threads == 4
    assert server_config.preload_app is False
    assert server_config.access_log_format.endswith("%(M)sms")
    assert server_config.http_protocols == ["h1"]
    assert server_config.http2_cleartext == "off"
    assert server_config.forwarded_allow_ips == ["127.0.0.1"]


@pytest.mark.parametrize(
    "headers",
    [
        b"Host: fixture.invalid\r\nTransfer-Encoding: unsupported\r\n",
        b"Host: fixture.invalid\r\nTransfer-Encoding: chunked\r\nContent-Length: 0\r\n",
        b"Host: fixture.invalid\r\nHost: other.invalid\r\n",
        b"Host: fixture.invalid\r\nTransfer-Encoding: chunked\r\nTransfer-Encoding: gzip\r\n",
    ],
)
def test_ambiguous_http_framing_is_rejected_in_memory(server_config, headers):
    with pytest.raises(ParseException):
        parse_request(server_config, headers)


def test_forwarded_scheme_is_honored_only_from_trusted_loopback(server_config):
    headers = b"Host: fixture.invalid\r\nX-Forwarded-Proto: https\r\n"
    assert parse_request(server_config, headers).scheme == "https"
    assert parse_request(server_config, headers, peer="203.0.113.15").scheme == "http"


def test_non_chunked_transfer_coding_forces_connection_close(server_config):
    headers = b"Host: fixture.invalid\r\nTransfer-Encoding: gzip\r\n"
    assert parse_request(server_config, headers).should_close()
