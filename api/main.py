"""QuakeScope API.

A small web API that serves recent earthquake data from the USGS Earthquake API
and measures itself. Every request is counted and timed, and the numbers are
published at /metrics for Prometheus to collect.
"""
import asyncio
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

USGS_BASE = os.getenv("USGS_BASE", "https://earthquake.usgs.gov/fdsnws/event/1")
# Be polite to the public USGS service: keep each answer for a while before asking again.
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "60"))
USER_AGENT = "QuakeScope-student-project/1.0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("quakescope")

# ---------------------------------------------------------------- metrics
# Counter: only goes up. Request rate and error rate are calculated from it.
REQUESTS = Counter(
    "http_requests_total", "Number of HTTP requests", ["method", "endpoint", "status"]
)
# Histogram: counts requests into time buckets. Latency percentiles come from it.
LATENCY = Histogram(
    "http_request_duration_seconds",
    "How long requests take, in seconds",
    ["endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
# Counts calls to USGS, so we can prove we stay polite (cache hits are free).
USGS_CALLS = Counter("usgs_lookups_total", "Lookups for USGS data", ["result"])
# Gauge: goes up and down. Requests being handled right now.
IN_PROGRESS = Gauge("http_requests_in_progress", "Requests being handled right now")

app = FastAPI(title="QuakeScope API", version="1.0.0")


@app.middleware("http")
async def measure(request: Request, call_next):
    """Runs around every request: start a timer, handle the request, then record it."""
    if request.url.path == "/metrics":  # do not count Prometheus's own visits
        return await call_next(request)

    start = time.perf_counter()
    status = 500  # if the code crashes, this is what gets recorded
    IN_PROGRESS.inc()
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        IN_PROGRESS.dec()
        elapsed = time.perf_counter() - start
        route = request.scope.get("route")
        # Use the route pattern, not the raw URL, so labels stay few and tidy.
        endpoint = route.path if route else "other"
        REQUESTS.labels(request.method, endpoint, str(status)).inc()
        LATENCY.labels(endpoint).observe(elapsed)
        log.info("%s %s -> %s in %.0f ms", request.method, request.url.path, status, elapsed * 1000)


# ---------------------------------------------------------------- USGS access
_cache: dict = {}


async def fetch_usgs(path: str, params: dict) -> dict:
    """Ask the USGS API a question. Answers are kept for CACHE_SECONDS."""
    key = (path, tuple(sorted(params.items())))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        USGS_CALLS.labels("cache_hit").inc()
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{USGS_BASE}/{path}", params=params, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        USGS_CALLS.labels("error").inc()
        log.warning("USGS request failed: %s", exc)
        raise HTTPException(status_code=502, detail="The USGS service did not answer")
    USGS_CALLS.labels("fetched").inc()
    _cache[key] = (time.time(), data)
    return data


# ---------------------------------------------------------------- endpoints
@app.get("/")
def home():
    return {
        "name": "QuakeScope API",
        "endpoints": ["/earthquakes/recent", "/earthquakes/count", "/health", "/metrics", "/docs"],
        "test_endpoints": ["/test/slow?delay=2", "/test/error?rate=0.9"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/earthquakes/recent")
async def recent(min_magnitude: float = Query(2.5, ge=0, le=10), limit: int = Query(10, ge=1, le=100)):
    """The most recent earthquakes at or above a magnitude."""
    data = await fetch_usgs(
        "query",
        {"format": "geojson", "orderby": "time", "limit": limit, "minmagnitude": min_magnitude},
    )
    quakes = []
    for f in data.get("features", []):
        p = f["properties"]
        quakes.append(
            {
                "place": p.get("place"),
                "magnitude": p.get("mag"),
                "time": datetime.fromtimestamp(p["time"] / 1000, timezone.utc).isoformat(),
            }
        )
    return {"count": len(quakes), "earthquakes": quakes}


@app.get("/earthquakes/count")
async def count(min_magnitude: float = Query(4.0, ge=0, le=10)):
    """How many earthquakes in the last 24 hours at or above a magnitude."""
    since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    data = await fetch_usgs(
        "count", {"format": "geojson", "starttime": since, "minmagnitude": min_magnitude}
    )
    return {"last_24_hours": data.get("count"), "min_magnitude": min_magnitude}


# Two endpoints that exist only so we can break the API on purpose in the demo.
@app.get("/test/slow")
async def slow(delay: float = Query(2.0, ge=0, le=10)):
    """Waits before answering, to create slow requests."""
    await asyncio.sleep(delay)
    return {"waited_seconds": delay}


@app.get("/test/error")
def error(rate: float = Query(0.9, ge=0, le=1)):
    """Fails with a 500 error some of the time, to create errors."""
    if random.random() < rate:
        raise HTTPException(status_code=500, detail="Deliberate test error")
    return {"ok": True}
