"""Regenerates dashboards/quakescope.json. Run: python generate_dashboard.py"""
import json
DS = {"type": "prometheus", "uid": "prometheus"}
W = "$__rate_interval"
RATE = f"sum(rate(http_requests_total[{W}]))"
ERR = f'(sum(rate(http_requests_total{{status=~"5.."}}[{W}])) or vector(0)) / sum(rate(http_requests_total[{W}]))'
def pct(q): return f"histogram_quantile({q}, sum by (le) (rate(http_request_duration_seconds_bucket[{W}])))"

def tgt(expr, legend="", ref="A"):
    return {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}

def stat(i, title, desc, expr, x, unit, steps, decimals=None):
    d = {"unit": unit, "thresholds": {"mode": "absolute", "steps": steps}}
    if decimals is not None: d["decimals"] = decimals
    return {"id": i, "type": "stat", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"x": x, "y": 0, "w": 8, "h": 4}, "targets": [tgt(expr)],
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"colorMode": "value", "graphMode": "area", "textMode": "value",
                        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}

def ts(i, title, desc, targets, x, y, unit, minv=0, stack=False):
    custom = {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 10 if stack else 0, "showPoints": "never"}
    if stack: custom["stacking"] = {"mode": "normal", "group": "A"}
    return {"id": i, "type": "timeseries", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"x": x, "y": y, "w": 12, "h": 8}, "targets": targets,
            "fieldConfig": {"defaults": {"unit": unit, "min": minv, "custom": custom}, "overrides": []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom"},
                        "tooltip": {"mode": "multi", "sort": "none"}}}

G, Y, R = {"color": "green", "value": None}, {"color": "yellow", "value": 0.5}, {"color": "red", "value": 1}
panels = [
    stat(1, "Requests per second", "How many requests the API handles each second (the Rate).",
         RATE, 0, "reqps", [{"color": "blue", "value": None}], decimals=1),
    stat(2, "Error rate", "Share of requests that fail with a 5xx status (the Errors).",
         ERR, 8, "percentunit", [G, {"color": "yellow", "value": 0.01}, {"color": "red", "value": 0.05}], decimals=1),
    stat(3, "p95 latency", "95 out of 100 requests are faster than this (the Duration).",
         pct(0.95), 16, "s", [G, Y, R], decimals=3),
    ts(4, "Request rate by endpoint", "Requests per second, one line per endpoint.",
       [tgt(f"sum by (endpoint) (rate(http_requests_total[{W}]))", "{{endpoint}}")], 0, 4, "reqps"),
    ts(5, "Latency percentiles", "p50 is the typical request. p95 and p99 show the slowest ones.",
       [tgt(pct(0.5), "p50", "A"), tgt(pct(0.95), "p95", "B"), tgt(pct(0.99), "p99", "C")], 12, 4, "s"),
    ts(6, "Error rate over time", "Percentage of requests that return a 5xx status.",
       [tgt(ERR, "5xx errors")], 0, 12, "percentunit"),
    ts(7, "Requests by status code", "Requests per second, split by HTTP status (200 = OK, 500 = server error).",
       [tgt(f"sum by (status) (rate(http_requests_total[{W}]))", "{{status}}")], 12, 12, "reqps", stack=True),
]
dash = {"uid": "quakescope", "title": "QuakeScope: API Telemetry", "tags": ["quakescope"],
        "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True,
        "refresh": "5s", "time": {"from": "now-15m", "to": "now"},
        "templating": {"list": []}, "annotations": {"list": []}, "panels": panels}
import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboards", "quakescope.json")
json.dump(dash, open(out, "w"), indent=2)
print("panels:", len(panels), "->", out)
