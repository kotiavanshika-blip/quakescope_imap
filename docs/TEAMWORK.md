# Teamwork: roles, commits and the repo

The brief asks for **one repo per group**, **meaningful commits from every member**, and **a stated role for each member** in the README.

## 1. Suggested roles (change to match your group)

| Role | Owns | Folder |
|---|---|---|
| API developer | The API, the `/metrics` page, tests, caching | `api/` |
| Prometheus and Docker | Scrape settings, `docker-compose.yml`, healthchecks | `prometheus/`, `docker-compose.yml` |
| Grafana dashboard | Data source, dashboard panels, PromQL | `grafana/` |
| Website and traffic | The two pages, load generator, screenshots | `site/`, `loadgen/` |
| Docs and research | README, research answers, demo script | `README.md`, `docs/` |

With 4 members, merge the last two. With 3, merge Prometheus/Docker with Grafana as well.
**Every member should still be able to explain every part** (the brief says any member may be asked).

## 2. One repo, many commits

One person creates the empty repo on GitHub and adds the others as collaborators. Then:

```
git clone <repo-url>
cd <repo>
git config user.name  "Your Name"
git config user.email "the email linked to YOUR GitHub account"
```

(If the email is not the one on your GitHub account, your commits will not show under your name.)

Work like this, each person on their own branch:

```
git checkout -b feature/grafana-dashboard
# ...edit files...
git add grafana/
git commit -m "Add error rate panel to the Grafana dashboard"
git push -u origin feature/grafana-dashboard
```

Open a pull request on GitHub and let a teammate review it. Merge to `main`.

## 3. What a meaningful commit looks like

- Small and about one thing: "Add 502 response when USGS fails", not "update".
- Says what and why in one line.
- Commit as you go. Do not upload everything in one commit at the end.

## 4. A commit plan (use as a checklist, one person per line)

| Who | Suggested commits |
|---|---|
| API developer | Add FastAPI skeleton and `/health` · Add USGS recent/count endpoints · Add request counter and latency histogram middleware · Add 60 s cache · Add `/test/slow` and `/test/error` · Add unit tests |
| Prometheus and Docker | Add Dockerfile for the API · Add `prometheus.yml` with 5 s scrape · Add `docker-compose.yml` · Add healthcheck and `depends_on` · Add `.env.example` and `.gitignore` |
| Grafana dashboard | Add data source provisioning · Add request-rate panels · Add latency percentile panel · Add error-rate panel · Export dashboard JSON |
| Website and traffic | Add load generator · Add overview page · Add live graphs page · Add break-it buttons · Add Grafana screenshots |
| Docs and research | Write README setup steps · Add research answers · Add architecture diagram · Write demo script · Add members and roles |

## 5. Before you submit

- [ ] Every member has commits (`git shortlog -sn` shows everyone).
- [ ] README has the members and roles table filled in.
- [ ] No `.env` or keys in the repo (`git ls-files | grep -i env` shows only `.env.example`).
- [ ] You added your own Grafana screenshots in `docs/screenshots/`.
- [ ] `docker compose up -d --build` works from a fresh clone.

## 6. Being polite to the public API

- The API **caches** every USGS answer for 60 seconds, so the load generator's traffic mostly never reaches USGS.
- The load generator only talks to **our own API**, never to USGS directly.
- The "Cause errors" and "Cause slow requests" buttons only call `/test/*`, which never contact USGS.
- The API sends a `User-Agent` that names the project.
- The `usgs_lookups_total{result="fetched|cache_hit|error"}` metric counts how many times USGS was really asked. In Prometheus, run `increase(usgs_lookups_total{result="fetched"}[5m])` to show the number is small.

With 9 different questions and a 60-second cache, USGS is asked at most about 9 times per minute, however many requests our API receives.
