# Food Donate — frontend

Framework-free static frontend (HTML + CSS + vanilla JS) for the
[Python backend](../backend/README.md). Keeps the original green "Food Donate"
branding; the old PHP-templated pages are in [`../legacy-php/`](../legacy-php/).

## Pages

| File | Purpose |
|------|---------|
| `index.html`   | Marketing landing — how it works, role explainer |
| `login.html`   | Sign in **and** register (role picker: restaurant / NGO / delivery) |
| `app.html`     | The authenticated app — renders a different dashboard per role |
| `about.html` / `contact.html` | Static info; contact page posts to `POST /api/feedback` |
| `assets/api.js`  | `window.FW` — API client, JWT session (localStorage), geolocation helper |
| `assets/app.js`  | Role-aware dashboards (restaurant / NGO / delivery / admin) |
| `assets/app.css` | Shared styles |

## Running it

It's fully static — serve the folder with anything:

```bash
cd frontend
python -m http.server 5173
```

Then open <http://localhost:5173>. The backend must be running (see
`../backend/README.md`) and its `ALLOWED_ORIGINS` must include the origin you
serve this from (e.g. `http://localhost:5173`).

### Pointing at the backend

`assets/api.js` defaults to `http://localhost:8000`. Override without editing:

* `?api=http://host:port` once in the URL (it's remembered in localStorage), or
* set `window.API_BASE` before `api.js` loads.

## What each role sees in `app.html`

* **Restaurant** — post a leftover-food donation (with pickup location / best-before), list & cancel own donations.
* **NGO** — browse donations near it ranked by distance, claim one (auto-assigns the nearest delivery partner), confirm receipt, release.
* **Delivery** — availability + live location toggle, "My tasks" (pickup → deliver), "Open pool" of unassigned jobs to accept.
* **Admin** — stats, all donations with manual "assign nearest delivery", user approve/deactivate, feedback inbox.

Geolocation uses the browser's `navigator.geolocation`; every location field also
accepts manual lat/lng entry.
