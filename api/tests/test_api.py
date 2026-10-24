"""Tests for the QuakeScope API. USGS is replaced by a fake, so no internet is needed."""
import re

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

FAKE_QUERY = {
    "features": [
        {"properties": {"place": "10 km N of Somewhere", "mag": 4.7, "time": 1760000000000}},
        {"properties": {"place": "Offshore", "mag": 3.1, "time": 1760000100000}},
    ]
}


@pytest.fixture(autouse=True)
def fresh_cache():
    main._cache.clear()


def metric_value(text, name, **labels):
    """Read one number out of the /metrics text."""
    wanted = [f'{k}="{v}"' for k, v in labels.items()]
    total = 0.0
    for line in text.splitlines():
        if line.startswith(name + "{") and all(w in line for w in wanted):
            total += float(line.rsplit(" ", 1)[1])
    return total


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_recent_returns_clean_list(monkeypatch):
    async def fake(path, params):
        return FAKE_QUERY

    monkeypatch.setattr(main, "fetch_usgs", fake)
    body = client.get("/earthquakes/recent").json()
    assert body["count"] == 2
    assert body["earthquakes"][0]["magnitude"] == 4.7
    assert body["earthquakes"][0]["time"].startswith("2025-")


def test_count(monkeypatch):
    async def fake(path, params):
        return {"count": 42}

    monkeypatch.setattr(main, "fetch_usgs", fake)
    assert client.get("/earthquakes/count?min_magnitude=5").json()["last_24_hours"] == 42


def test_bad_input_is_rejected():
    assert client.get("/earthquakes/recent?limit=0").status_code == 422


def test_usgs_answers_are_cached(monkeypatch):
    calls = {"n": 0}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return FAKE_QUERY

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, params=None, headers=None):
            calls["n"] += 1
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)
    client.get("/earthquakes/recent")
    client.get("/earthquakes/recent")
    assert calls["n"] == 1  # the second request came from the cache


def test_usgs_failure_gives_502(monkeypatch):
    class BrokenClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, params=None, headers=None):
            raise main.httpx.ConnectError("no internet")

    monkeypatch.setattr(main.httpx, "AsyncClient", BrokenClient)
    assert client.get("/earthquakes/recent").status_code == 502


def test_slow_endpoint_waits():
    import time

    start = time.perf_counter()
    assert client.get("/test/slow?delay=0.2").status_code == 200
    assert time.perf_counter() - start >= 0.2


def test_error_endpoint_fails_and_is_counted_as_500():
    before = metric_value(client.get("/metrics").text, "http_requests_total", endpoint="/test/error", status="500")
    assert client.get("/test/error?rate=1").status_code == 500
    after = metric_value(client.get("/metrics").text, "http_requests_total", endpoint="/test/error", status="500")
    assert after == before + 1


def test_requests_are_counted_and_timed():
    client.get("/health")
    text = client.get("/metrics").text
    assert metric_value(text, "http_requests_total", endpoint="/health", status="200") >= 1
    assert metric_value(text, "http_request_duration_seconds_count", endpoint="/health") >= 1
    assert "http_request_duration_seconds_bucket" in text


def test_unknown_urls_share_one_label():
    client.get("/random-1")
    client.get("/random-2")
    text = client.get("/metrics").text
    assert "random-1" not in text
    assert metric_value(text, "http_requests_total", endpoint="other", status="404") >= 2


def test_metrics_endpoint_is_not_counted():
    client.get("/metrics")
    assert 'endpoint="/metrics"' not in client.get("/metrics").text


def test_usgs_lookups_are_counted(monkeypatch):
    """One real lookup, then cache hits: this is how we show we respect USGS."""
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return FAKE_QUERY
    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, params=None, headers=None):
            assert "User-Agent" in headers
            return FakeResp()
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)
    def count(result):
        return metric_value(client.get("/metrics").text, "usgs_lookups_total", result=result)
    before = count("fetched"), count("cache_hit")
    for _ in range(3):
        client.get("/earthquakes/recent?min_magnitude=4&limit=5")
    assert count("fetched") - before[0] == 1
    assert count("cache_hit") - before[1] == 2
