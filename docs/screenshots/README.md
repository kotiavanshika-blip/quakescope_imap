# Screenshots

These are captures of the **website** from a test run with generated traffic.

| File | Shows |
|---|---|
| `overview.png` | The Overview page with the diagram |
| `live-normal.png` | Live graphs during normal traffic |
| `live-errors.png` | Live graphs while "Cause errors" is running: the error rate jumps |
| `live-slow.png` | Live graphs while "Cause slow requests" is running: p95 and p99 rise |
| `mobile-index.png`, `mobile-live.png` | The same pages on a phone-width screen |

**There are no Grafana screenshots here**, because Grafana could not be run where these were taken. Take your own and save them in this folder:

1. `grafana-dashboard.png`: http://localhost:3000, the whole *QuakeScope: API Telemetry* dashboard during normal traffic
2. `grafana-errors.png`: the same dashboard while you press **Cause errors** on the website
3. `prometheus-targets.png`: http://localhost:9090/targets with `quakescope-api` showing UP

Tip: set the Grafana time range to *Last 15 minutes*.
