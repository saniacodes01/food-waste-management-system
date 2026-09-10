# Food Waste Management — Python backend

FastAPI + async SQLAlchemy + PostGIS. Replaces the old PHP/MySQL backend
(kept for reference in [`../legacy-php/`](../legacy-php/)). The browser UI that
consumes this API lives in [`../frontend/`](../frontend/README.md).

## The flow

```
RESTAURANT                NGO                     DELIVERY PARTNER            ADMIN
----------                ---                     ----------------           -----
register (self)           register (self)         register (self)            seeded
post leftover food  ─►  sees nearby donations
                        claims one          ─►  nearest free partner
                                                 is auto-assigned
                                                 (or picks from the pool)
                          ◄── confirms receipt ── delivers to the NGO
                                                                              oversees
                                                                              everything,
                                                                              can reassign
```

* **Anyone** can register as a `restaurant`, an `ngo`, or a `delivery` partner
  (`POST /api/auth/register`). `admin` accounts are created with `seed_admin.py`.
* A **restaurant** posts leftover food with a pickup location.
* Nearby **NGOs** (serving needy people) see it ranked by distance and claim it.
* On claim, the system finds the **nearest available delivery partner** within
  `MATCH_RADIUS_KM` and assigns them. If nobody is free, the job sits in the
  delivery **pool** for any partner to accept.
* The delivery partner marks `pickup` → `deliver`; the NGO can `confirm-received`.
* Every state change is written to `donation_events` for an audit trail.

"Nearest" everywhere is a PostGIS `ST_DWithin` / `ST_Distance` query on
`Geography(POINT)` columns.

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit DATABASE_URL + SECRET_KEY
```

You need PostgreSQL with the PostGIS extension. Create the database once:

```bash
createdb foodwaste_db
psql -d foodwaste_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

(The app also runs `CREATE EXTENSION IF NOT EXISTS postgis` and `create_all` on
startup, so if your DB user has rights that is all that is needed.)

Seed an admin and run:

```bash
python seed_admin.py "Site Admin" admin@example.com "change-me"
uvicorn main:app --reload --port 8000
```

Interactive API docs: <http://localhost:8000/docs>

## Endpoint map

| Area       | Endpoints |
|------------|-----------|
| Auth       | `POST /api/auth/register`, `POST /api/auth/login`, `GET/PATCH /api/auth/me` |
| Restaurant | `POST /api/donations`, `GET /api/donations/mine`, `PATCH /api/donations/{id}`, `POST /api/donations/{id}/cancel` |
| NGO        | `GET /api/ngo/donations/available`, `POST /api/ngo/donations/{id}/claim`, `GET /api/ngo/donations/claimed`, `POST /api/ngo/donations/{id}/confirm-received`, `POST /api/ngo/donations/{id}/release` |
| Delivery   | `PATCH /api/delivery/availability`, `GET /api/delivery/tasks`, `GET /api/delivery/pool`, `POST /api/delivery/donations/{id}/accept\|pickup\|deliver\|decline` |
| Admin      | `GET /api/admin/stats`, `GET/PATCH /api/admin/users`, `GET /api/admin/donations`, `POST /api/admin/donations/{id}/assign/{delivery_id}`, `GET /api/admin/donations/{id}/nearest-delivery` |
| Feedback   | `POST /api/feedback` (public), `GET /api/feedback` (admin) |

Auth is a Bearer JWT from `login`/`register`: `Authorization: Bearer <token>`.

## Donation status

`available → claimed → assigned → picked_up → delivered`
plus `cancelled` (restaurant/NGO withdrew) and `expired` (past `best_before`).

## Migrating old data

The old MySQL dump is at [`../legacy-php/database/demo.sql`](../legacy-php/database/demo.sql).
Rough mapping to the new schema:

| Old (MySQL)        | New (`users` / `donations`) |
|--------------------|-----------------------------|
| `login`            | `users` with `role='restaurant'` (old "users" were donors) |
| `admin`            | `users` with `role='ngo'` (old admin = trusts/NGOs) + one real `role='admin'` |
| `delivery_persons` | `users` with `role='delivery'`, `city` → `city` |
| `food_donations`   | `donations`; `assigned_to` → `claimed_by_ngo_id`, `delivery_by` → `delivery_by_id`, `location` → `city` |
| `user_feedback`    | `feedback` |

Old rows have no lat/lng — backfill from `city`/`address` via geocoding before
the distance-based matching will work for them.
