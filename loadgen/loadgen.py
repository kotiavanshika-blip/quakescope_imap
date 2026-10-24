"""Sends a steady trickle of normal requests (about 5 per second) to the API,
so the dashboard always has something to show."""
import os
import random
import time

import httpx

BASE = os.getenv("TARGET", "http://api:8000")

# Different magnitudes mean different USGS questions, so some answers come from
# the cache (fast) and some from USGS (slower). That gives the latency graph some shape.
PATHS = (
    ["/health"] * 2
    + [f"/earthquakes/recent?min_magnitude={m}&limit=10" for m in (2.5, 3, 3.5, 4, 4.5, 5)] * 2
    + [f"/earthquakes/count?min_magnitude={m}" for m in (3, 4, 5)]
)

print(f"Load generator sending requests to {BASE}", flush=True)
with httpx.Client(timeout=15) as client:
    while True:
        path = random.choice(PATHS)
        try:
            client.get(BASE + path)
        except httpx.HTTPError as exc:
            print("request failed:", exc, flush=True)
            time.sleep(2)
        time.sleep(random.uniform(0.1, 0.3))
