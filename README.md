# Food Waste Management System

Collect surplus / leftover food from restaurants, canteens, marriage halls and
events, and get it to the people who need it — with the nearest delivery partner
carrying it across.

Originally a PHP/MySQL project, now a **Python (FastAPI) API + a framework‑free
JSON frontend** on **PostgreSQL + PostGIS**. The old code is kept under
[`legacy-php/`](legacy-php/) for reference.

```
┌────────────┐     posts leftover food      ┌───────────────┐
│ RESTAURANT │ ───────────────────────────► │   DONATION    │
└────────────┘                              │  "available"  │
                                            └───────┬───────┘
┌────────────┐   sees donations near it,           │ claim
│    NGO     │ ◄───────── ranked by distance ──────┘
└─────┬──────┘                                      │ auto-assign
      │ confirms receipt                            ▼
      │                                   ┌────────────────────┐
      └────────────────────────────────── │  DELIVERY PARTNER  │
                pickup → deliver          │  (nearest & free)  │
                                          └────────────────────┘
              ADMIN oversees everything and can reassign delivery
```

---

## Roles — anyone can self‑register

| Role | Who | What they do |
|------|-----|--------------|
| **Restaurant** | hotels, canteens, halls, individuals | Post leftover food with a pickup location and best‑before time; track / cancel their donations |
| **NGO** | trusts, charities that serve needy people | Browse donations near them (nearest first), claim one, confirm receipt |
| **Delivery partner** | volunteers, riders | Go on shift with a live location; get auto‑assigned the nearest pickups, or grab jobs from an open pool; mark *picked up* → *delivered* |
| **Admin** | platform operator | Dashboard stats, all donations, approve / deactivate accounts, manually reassign delivery, read feedback. Created with a script, not self‑registered. |

**Donation lifecycle:** `available → claimed → assigned → picked_up → delivered`
(plus `cancelled`, `expired`). Every change is written to an audit timeline.

---

## Prerequisites

* **Python 3.11+**
* **PostgreSQL 14+** with the **PostGIS** extension
* A modern browser (the frontend uses `navigator.geolocation` for "near me")

---

## 1. Set up the database

```bash
# as a Postgres superuser
createdb foodwaste_db
psql -d foodwaste_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Don't have rights to create a database (shared server)? You can instead put every
table in a named **schema** of an existing database — see `DB_SCHEMA` in
`backend/.env.example`.

---

## 2. Run the backend (API)

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit DATABASE_URL + SECRET_KEY
python seed_admin.py "Site Admin" admin@example.com "a-strong-password"

uvicorn main:app --reload --port 8000
```

* API root: <http://localhost:8000>
* Interactive docs (try every endpoint): <http://localhost:8000/docs>

Tables are created automatically on first start.

---

## 3. Run the frontend

It's static files — serve the folder with anything:

```bash
cd frontend
python -m http.server 5173
```

Open <http://localhost:5173>.

The frontend talks to `http://localhost:8000` by default. To point it elsewhere,
add `?api=https://your-api-host` to the URL once (it's remembered), and make sure
that origin is listed in the backend's `ALLOWED_ORIGINS`.

---

## 4. Use it

1. Open the frontend, click **Register**, pick a role (Restaurant / NGO / Delivery),
   fill in the form and allow location access (or type lat/lng manually).
2. **As a restaurant** — "Post food", enter what's available and the pickup point.
3. **As an NGO** — "Available near me" shows nearby donations with distances;
   click **Claim**. The nearest free delivery partner is auto‑assigned.
4. **As a delivery partner** — toggle **Available**, set your location. Claimed jobs
   appear under **My tasks** (or **Open pool** if none was free at claim time).
   Mark **Picked up**, then **Delivered**.
5. **As admin** — log in with the seeded account to see stats, approve accounts,
   reassign delivery and read feedback.

---

## Project layout

```
backend/        FastAPI app — routes/ services/ utils/, models.py, schemas.py
  seed_admin.py     create the first admin account
  README.md         endpoint map + data model + old-data migration table
frontend/       static site — index/login/app.html + assets/{api,app}.js, app.css
  README.md         page-by-page guide
legacy-php/      the original PHP/MySQL app + static pages (reference only)
```

## Tech

| Layer | Choice |
|-------|--------|
| API | FastAPI, async SQLAlchemy 2.0, Pydantic v2 |
| DB | PostgreSQL + PostGIS (`ST_DWithin` / `ST_Distance` for "nearest") |
| Auth | JWT (PyJWT) + bcrypt (passlib) |
| Frontend | Plain HTML / CSS / vanilla JS — no build step |

See [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md) for details, and the migration
mapping from the old MySQL schema.
