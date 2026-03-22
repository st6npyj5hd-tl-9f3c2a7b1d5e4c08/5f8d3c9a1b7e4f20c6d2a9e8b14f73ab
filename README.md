# San Diego Static Snapshot Publisher

This repository publishes static snapshots of four public San Diego weather/school resources to GitHub Pages.

It is **not** a live proxy. Upstream data is fetched on a schedule, written to files in `docs/api`, and then served as static assets.

## Published endpoints

After enabling GitHub Pages (see below), these files are available under your Pages base URL:

- `/api/school-calendar.pdf`
- `/api/area-forecast-discussion.txt`
- `/api/forecast.dwml`
- `/api/hourly-forecast.dwml`
- `/api/status.json`
- `/openapi.yaml`

## Enable GitHub Pages

1. Go to **Settings → Pages** in your repository.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Select your default branch and the `/docs` folder.
4. Save.

Once published, files will be served from:

`https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab/`

## Scheduled refresh and manual runs

The workflow at `.github/workflows/fetch-and-deploy.yml`:

- runs every 6 hours (`0 */6 * * *`)
- supports manual runs via **Actions → Fetch and publish static snapshots → Run workflow**
- fetches all sources, updates `docs/api/*` and `docs/openapi.yaml`, and commits changes when needed

If one source fails, the previous published file is kept. The run fails only when all four sources fail.

## OpenAPI base URL replacement

`docs/openapi.yaml` uses a placeholder server URL:

`https://st6npyj5hd-tl-9f3c2a7b1d5e4c08.github.io/5f8d3c9a1b7e4f20c6d2a9e8b14f73ab`

Replace that single value with your real Pages base URL.

## Notes on freshness and caching

- `docs/api/status.json` records the latest fetch attempt with per-source success/failure metadata.
- GitHub Pages and intermediary caches may serve slightly older content for a short period after a workflow run.
