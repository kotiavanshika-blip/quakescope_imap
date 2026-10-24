# Demo script and viva questions

## Before you present

1. Open a terminal in the project folder and run `docker compose up -d --build`.
2. Run `docker compose ps` and wait until everything is running (about a minute).
3. Open these tabs: the website (`localhost:8081`), Grafana (`localhost:3000`), `localhost:8000/metrics`, and `localhost:9090/targets`.
4. Browser zoom 110 to 125% so the back row can read it.
5. Practise the button demo once beforehand.

## Ten-minute demo (then 5 minutes of questions)

The brief gives 10 minutes live. Split it so **every member speaks**: one person per part, using the roles in the README. Suggested split: API (2 min), Prometheus and Docker (2 min), Grafana (2 min), break-it demo (2 min), research and wrap-up (2 min). The table below is the core 5-minute flow; stretch each step with the "show" ideas underneath.

## Core flow (5 minutes)

| Time | Do | Say |
|---|---|---|
| 0:00 | Website, Overview page | "Our API serves earthquake data from USGS. The project is about measuring the API: request rate, latency and error rate. Prometheus collects the numbers and Grafana shows them." |
| 1:00 | Show the diagram | "The load generator sends requests. The API counts and times each one. Prometheus visits the API's metrics page every 5 seconds. Grafana asks Prometheus for the numbers. Prometheus pulls; the API does not push." |
| 1:45 | `localhost:8000/metrics`, then `localhost:9090/targets` | "This is the raw text the API publishes. This is Prometheus: the API shows UP, which means the scrape works." |
| 2:30 | Grafana dashboard | "Top row: requests per second, error rate, p95 latency. Below: the same over time. We use percentiles because an average hides slow requests." |
| 3:15 | Website, Live graphs, press **Cause errors** | "Now I will break it on purpose. The page sends requests to an endpoint that fails 9 times out of 10. Watch the error rate." (It appears after 5 to 15 seconds.) Show Grafana as well. |
| 4:15 | Press **Cause slow requests** | "Now the endpoint is slow, not failing. The error rate stays flat but p95 and p99 rise. Slow is not the same as broken, so we watch both." |
| 4:45 | Summary | "Metrics from the API, collected by Prometheus, shown by Grafana, all started with one Compose command." |

The buttons need 30 seconds each, and they stop by themselves.

### Extra material for the other 5 minutes

- Show `docker compose ps` and say "five containers, one command".
- Open `localhost:8000/docs` and call `/earthquakes/recent` live. Call it twice and show `usgs_lookups_total` in `/metrics`: one `fetched`, then `cache_hit`. This proves caching and politeness to USGS.
- In Prometheus (`localhost:9090`), type `sum(rate(http_requests_total[1m]))` and press Execute. It is the same query Grafana uses.
- Run `docker compose logs api` and show the one-line-per-request log.
- Say what you would add next: Loki for logs, OpenTelemetry for traces, an alert rule for error rate above 5%.

## Questions you may be asked

**How do you avoid hammering the public USGS API?**
Every USGS answer is cached for 60 seconds, the load generator only calls our own API, the test endpoints never contact USGS, and the `usgs_lookups_total` metric shows how many real calls were made.

**Where are your keys?**
USGS needs no key, so there are none. Settings go in `.env`, which is ignored by git; `.env.example` shows the format.

**What is the difference between metrics, logs and traces?**
Metrics are numbers over time ("is something wrong?"). Logs are text records of single events ("what happened?"). Traces follow one request through several services ("where did the time go?"). We use metrics. The API also prints a log line per request. We do not use traces, because there is only one service.

**How does Prometheus get the data?**
It pulls. Every 5 seconds it requests the API's `/metrics` page, reads the text and stores each value with the time. The interval is set in `prometheus/prometheus.yml`.

**Why pull and not push?**
Prometheus controls how often it collects, and the application stays simple. It also notices when a program stops answering, because the scrape fails and the built-in `up` metric becomes 0.

**What is a percentile?**
p95 is the time that 95 out of 100 requests are faster than. It shows how bad the slow requests are. p50 is the typical request and p99 is almost the worst.

**Why not use the average?**
An average hides slow requests. If 95 requests take 0.1 s and 5 take 10 s, the average is about 0.6 s, yet 5 users waited 10 seconds.

**What does error rate show?**
The share of requests that fail: failed divided by all. We count status 500 to 599 as failures. For example, 3 failures in 100 requests is 3%.

**How do you get percentiles from a histogram?**
The API counts every request into buckets such as "under 0.1 s". Prometheus's `histogram_quantile` uses those bucket counts to estimate the percentile. It is an estimate, because it does not know exact times.

**What does `rate()` do?**
A counter only grows. `rate` measures how fast it grows per second over a time window, such as the last minute.

**What are the three metric types you used?**
Counter (`http_requests_total`), histogram (`http_request_duration_seconds`) and gauge (`http_requests_in_progress`).

**Why do unknown URLs share the label `other`?**
Every different label value creates a new time series. If random URLs each got their own label, the number of series could grow without limit and overload Prometheus.

**How is the dashboard created?**
Grafana loads the data source and the dashboard file from the `grafana/` folder when it starts (this is called provisioning), so it is the same on every computer.

**What happens if the API crashes?**
Prometheus's scrape fails and `up` becomes 0, so the target shows DOWN on the targets page. We did not add an alert rule for it. That would be a good next step with Alertmanager.

**Why does the graph take a few seconds to react?**
Prometheus collects numbers every 5 seconds and each rate looks at a window of the last 20 to 30 seconds, so changes appear gradually.

**What would you add next?**
Alert rules with Alertmanager, central logs with Loki, and distributed tracing with OpenTelemetry once there are several services.

## Be honest if asked

- We do not have traces or central logs. Only metrics are collected.
- The load generator creates the normal traffic. The error and slow endpoints exist only for the demonstration.
