# RaceTrace — System Architecture

## Overview

RaceTrace is a web platform for uploading, storing, visualising, and comparing motorsport lap telemetry data. Users upload CSV files exported from in-car data loggers (currently TrackAddict), and the platform parses them, stores the structured data, and presents interactive charts and maps.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI 0.111 |
| ORM | SQLAlchemy 2.0 (declarative mapped columns) |
| Database | PostgreSQL 16 (production) · SQLite (tests) |
| Migrations | Alembic |
| Auth | JWT (python-jose) · bcrypt via passlib 1.7.4 |
| File storage | Local filesystem (`uploads/`) |
| Frontend | Server-rendered Jinja2 HTML · vanilla JS |
| Maps | Leaflet.js 1.9 |
| Charts | Chart.js 4 |
| Containerisation | Docker + docker-compose |

---

## Directory Layout

```
racetrace/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py          # Register, login, OAuth, refresh
│   │       ├── sessions.py      # Session CRUD + file upload
│   │       ├── laps.py          # Lap detail, telemetry, compare
│   │       ├── cars.py          # Car CRUD (per user)
│   │       ├── tracks.py        # Track + configuration read/admin-write
│   │       ├── leaderboard.py   # Public best laps per config
│   │       ├── events.py        # Event grouping
│   │       ├── admin.py         # Superuser management endpoints
│   │       ├── users.py         # User profile
│   │       ├── web.py           # HTML page routes (no JSON)
│   │       └── router.py        # Mounts all v1 routers
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── lap.py
│   │   ├── track.py / track_configuration.py
│   │   ├── car.py
│   │   ├── event.py
│   │   ├── refresh_token.py
│   │   └── oauth_account.py
│   ├── schemas/                 # Pydantic request/response models
│   ├── services/
│   │   ├── session_importer.py  # Orchestrates file → DB flow
│   │   ├── storage.py           # File save / path helpers
│   │   └── telemetry/
│   │       ├── parser.py        # TrackAddict CSV → Python dicts
│   │       ├── comparator.py    # Distance-based lap comparison
│   │       └── processor.py     # Post-parse enrichment (sectors etc.)
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── sessions/  (list, detail)
│   │   ├── laps/      (detail, compare)
│   │   ├── cars/      (list)
│   │   ├── tracks/    (list, detail)
│   │   └── admin/     (dashboard)
│   ├── config.py                # pydantic-settings (reads .env)
│   ├── database.py              # Engine + Base + get_db
│   └── main.py                  # FastAPI app, middleware, mounts
├── alembic/                     # DB migration scripts
├── tests/
│   ├── conftest.py              # Fixtures: in-memory DB, client, helpers
│   ├── test_auth.py
│   ├── test_laps.py
│   ├── test_api_sessions.py
│   ├── test_parser.py
│   └── test_comparator.py
├── docs/
│   └── SYSTEM.md                # ← this file
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Data Model

```
User ──< Session >── TrackConfiguration ──< Track
          │
          ├──< Lap
          │      └── gps_track (JSON array)
          │
          ├── Car (optional FK)
          └── Event (optional FK)

User ──< Car
User ──< RefreshToken
User ──< OAuthAccount
```

### Key tables

**users** — `id, username, email, hashed_password, is_active, is_superuser, failed_login_attempts, locked_until`

**sessions** — `id, user_id, track_configuration_id, car_id, event_id, session_type, date, is_public, source_file_path, app_source, vehicle_hint`

**laps** — `id, session_id, lap_number, lap_time_ms, is_valid, is_outlap, is_inlap, gps_track (JSON), max_speed_kmh, avg_speed_kmh`

**tracks / track_configurations** — `track(id, name, country, city)` · `config(id, track_id, name, length_meters, num_sectors, start_finish_lat/lon, layout_data, is_default)`

**cars** — `id, user_id, make, model, year, category, drivetrain, power_hp, weight_kg, engine_cc, notes`

---

## Authentication

### JWT flow
1. `POST /api/v1/auth/login` (form data) → returns `access_token` (Bearer, 15 min)
2. Sets `refresh_token` HttpOnly cookie (30 days, stored hashed in DB)
3. `POST /api/v1/auth/refresh` — exchanges refresh cookie for a new access token
4. `POST /api/v1/auth/logout` — revokes refresh token + clears cookie

### Admin token
`POST /api/v1/auth/admin/login` — issues a 2-hour token with `role: admin` claim; required for all `/admin/` endpoints.

### OAuth
Google and GitHub OAuth providers are supported via `authlib`. Configured via `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` environment variables.

### Brute-force protection
5 failed login attempts lock the account for 15 minutes (`locked_until` column).

---

## File Upload & Parsing Pipeline

```
POST /api/v1/sessions/upload (multipart, one file)
    │
    ├─ storage.save_upload()          # writes to uploads/<user_id>/<uuid>.<ext>
    │
    └─ session_importer.import_file()
         │
         ├─ parser.parse(path)        # TrackAddict CSV → list[lap_dict]
         │     ├─ reads metadata from # comment lines
         │     ├─ splits rows by Lap column
         │     ├─ normalises channel names → snake_case
         │     └─ extracts gps_track [[ts, lat, lon], ...]
         │
         ├─ Creates Session record (date from file metadata)
         │
         └─ For each lap_dict:
              └─ Creates Lap record (lap_time_ms, gps_track, stats)
```

Supported format: **TrackAddict CSV** (`.csv`). The parser detects the format from the `# App` metadata comment. Unsupported formats raise `ValueError`.

---

## Telemetry & Comparison

### Distance axis
All telemetry is presented on a **distance (metres) x-axis** rather than time. Distance is computed by integrating GPS or OBD speed:

```
distance[i] = distance[i-1] + avg_speed_kmh * dt / 3.6
```

### Lap comparison (`POST /api/v1/laps/compare`)
Given N lap IDs:
1. Parse each session's source file and find the lap by `lap_number`
2. Compute a cumulative distance array per lap
3. Resample all telemetry channels to a **common 500-point distance axis** using linear interpolation (`np.interp`)
4. Compute **Delta-T**: for each distance point `d`, `delta(d) = time_at_distance(comparison, d) − time_at_distance(reference, d)` — positive means slower than reference

### `GET /api/v1/laps/{id}/telemetry`
Returns:
- `channels`: list of `{name, unit, data[], timestamps[]}` — `timestamps` is the distance axis (metres)
- `distance_m`: the common distance array (same length as channel data)
- `gps_track`: `[[ts, lat, lon], ...]` for Leaflet map

---

## Frontend Architecture

All pages are server-rendered Jinja2 templates that serve as shells. Data is loaded client-side via fetch calls to the JSON API using a JWT stored in `localStorage`.

```javascript
// All API calls use this helper (defined in base.html)
function authHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
}
```

### Pages

| URL | Template | Description |
|---|---|---|
| `/` | `index.html` | Landing page |
| `/sessions` | `sessions/list.html` | My sessions + upload |
| `/sessions/{id}` | `sessions/detail.html` | Session laps + edit |
| `/laps/{id}` | `laps/detail.html` | Lap telemetry + GPS map |
| `/compare` | `laps/compare.html` | Multi-lap comparison |
| `/tracks` | `tracks/list.html` | Public track directory |
| `/tracks/{id}` | `tracks/detail.html` | Track + GPS maps per config |
| `/cars` | `cars/list.html` | My cars CRUD |
| `/admin` | `admin/dashboard.html` | Admin panel |

---

## API Reference (summary)

All endpoints under `/api/v1/`. Authentication via `Authorization: Bearer <token>` header.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | Get access token |
| POST | `/auth/refresh` | cookie | Refresh access token |
| GET | `/sessions/` | user | List my sessions |
| POST | `/sessions/` | user | Create session |
| POST | `/sessions/upload` | user | Upload telemetry file |
| GET | `/sessions/{id}` | user | Session detail |
| PATCH | `/sessions/{id}` | owner | Update session |
| DELETE | `/sessions/{id}` | owner | Delete session |
| GET | `/laps/{id}` | user | Lap detail |
| GET | `/laps/{id}/telemetry` | user | Lap telemetry channels |
| POST | `/laps/compare` | user | Compare N laps |
| GET | `/cars/` | user | List my cars |
| POST | `/cars/` | user | Add a car |
| PATCH | `/cars/{id}` | owner | Update car |
| DELETE | `/cars/{id}` | owner | Delete car |
| GET | `/tracks/` | — | List all tracks |
| GET | `/tracks/{id}` | — | Track detail + best lap GPS |
| POST | `/tracks/` | superuser | Create track |
| GET | `/leaderboard/` | — | Best public laps per config |
| PATCH | `/admin/tracks/{id}` | admin | Update track name/country |
| GET | `/admin/users` | admin | List all users |

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://racetrace:racetrace@localhost:5432/racetrace` | Production DB |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `UPLOAD_DIR` | `uploads` | File upload directory |
| `MAX_UPLOAD_SIZE_MB` | `50` | Upload size cap |
| `GOOGLE_CLIENT_ID/SECRET` | — | Google OAuth |
| `GITHUB_CLIENT_ID/SECRET` | — | GitHub OAuth |
| `OAUTH_REDIRECT_BASE_URL` | `http://localhost:8000` | OAuth callback base |

---

## Running Locally

```bash
# Start database
docker-compose up -d db

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Running Tests

```bash
pytest tests/
```

Tests use an **in-memory SQLite** database (`StaticPool`) — no external services required. All 41 tests pass in ~14 seconds.

---

## Deployment

```bash
docker-compose up --build
```

The `docker-compose.yml` starts:
- **app** — FastAPI on port 8000 (uvicorn)
- **db** — PostgreSQL 16
- **redis** — Redis (reserved for future background tasks)
