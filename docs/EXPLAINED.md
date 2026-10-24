# QuakeScope explained

This page explains the whole project in plain English, so everyone in the team can describe it.

## The idea in one sentence

We built an API that serves earthquake data, and then built the tools that **watch the API**: how busy it is, how fast it answers and how often it fails.

Think of a restaurant kitchen. The API is the kitchen. Prometheus is someone who writes down, every 5 seconds, how many orders came in, how long they took and how many went wrong. Grafana is the screen on the wall that turns those notes into graphs.

## The path of one request

1. A client (here, our load generator, or a button on the website) asks the API for something, such as `/earthquakes/recent`.
2. The API's **middleware** sees the request first. Middleware is a piece of code that runs around every request. It starts a stopwatch.
3. The API answers. If the answer was asked for in the last 60 seconds, it reuses the saved copy (a **cache**). Otherwise it asks USGS.
4. The middleware stops the stopwatch. It adds 1 to a counter for this endpoint and status code, and it records the time in a histogram.
5. Every 5 seconds, Prometheus visits `/metrics`, reads all the counters and stores them with the time.
6. Grafana (or the website) asks Prometheus for the numbers and draws graphs.

## What each part does

| Part | What it does | Why we need it |
|---|---|---|
| API (`api/main.py`) | Serves earthquakes. Counts and times every request. Shows the numbers at `/metrics`. | It is the thing being watched |
| Prometheus | Reads `/metrics` every 5 seconds and keeps the history | Without a history there is nothing to graph |
| Grafana | Draws the dashboard | Graphs are much easier to read than raw numbers |
| Load generator | Sends about 4 requests per second | Without traffic the graphs would be flat |
| Website | Overview, live graphs and notes | A friendly way to show the project |
| Docker Compose | Starts all of the above with one command | Anyone can run it the same way |

## The numbers the API publishes

| Metric | Type | Meaning |
|---|---|---|
| `http_requests_total` | Counter | How many requests, split by endpoint, method and status code |
| `http_request_duration_seconds` | Histogram | How long requests take, counted into time buckets |
| `http_requests_in_progress` | Gauge | How many requests are being handled right now |

- A **counter** only goes up, like an odometer. We look at how fast it grows (`rate`).
- A **gauge** goes up and down, like a speedometer.
- A **histogram** sorts each request into a bucket ("under 0.1 s", "under 0.25 s" and so on). From those bucket counts Prometheus can estimate percentiles.

The `/metrics` page itself is not counted, otherwise Prometheus's own visits would inflate the numbers. Unknown URLs are all counted under the label `other`, so a stream of random URLs cannot create thousands of separate time series.

## The three graphs the brief asks for

- **Request rate:** `sum(rate(http_requests_total[1m]))`. The counter grows; `rate` turns that growth into requests per second.
- **Error rate:** failed requests per second divided by all requests per second. A request counts as failed when its status is 500 to 599.
- **Latency:** `histogram_quantile(0.95, ...)` estimates p95, the time that 95 out of 100 requests beat. We also show p50 and p99.

Why percentiles and not the average? If 95 requests take 0.1 s and 5 take 10 s, the average is about 0.6 s and looks fine, but 5 users waited 10 seconds. p95 and p99 show that.

## What happens when you press the buttons

The buttons are on the website's **Live graphs** page.

- **Cause errors:** the page sends many requests to `/test/error`, an endpoint that fails 9 times out of 10 with a 500 status. The API counts those as 500s, Prometheus collects the counts, and the error rate jumps. It takes 5 to 15 seconds to appear because Prometheus only visits every 5 seconds.
- **Cause slow requests:** the page sends requests to `/test/slow`, which waits 2 seconds before answering with a normal 200. The error rate does not change, because slow is not the same as failing, but p95 and p99 rise to about 2 seconds.

Both stop by themselves after 30 seconds and the graphs return to normal.

## Where to look in the code

| File | What is in it |
|---|---|
| `api/main.py` | The metrics, the middleware, the endpoints |
| `api/tests/test_api.py` | 11 tests: counting, labels, caching, errors |
| `prometheus/prometheus.yml` | The scrape interval (5 s) and the two targets |
| `grafana/provisioning/` | Tells Grafana where Prometheus is and where the dashboard file is |
| `grafana/dashboards/quakescope.json` | The dashboard (7 panels) |
| `docker-compose.yml` | The five containers and how they connect |
| `site/` | The three web pages |

## Words you may be asked about

| Word | Plain meaning |
|---|---|
| Metrics | Numbers measured over time |
| Scrape | Prometheus visiting `/metrics` to copy the numbers |
| Label | A tag on a metric, such as `status="500"` |
| PromQL | The language for asking Prometheus questions |
| Provisioning | Setting Grafana up from files instead of clicking |
| p95 | 95 out of 100 requests are this fast or faster |
| 5xx | Any server error, status 500 to 599 |
| Container | A sealed box holding one program |
