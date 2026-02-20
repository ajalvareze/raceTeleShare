# RaceTrace

Upload, visualise, and compare motorsport lap telemetry data.

Upload a CSV file from your data logger, get interactive speed/throttle/brake charts on a distance axis, a GPS track map, and side-by-side lap comparison with Delta-T.

---

## Features

- **Session upload** — drag-and-drop a TrackAddict CSV; all laps are parsed and stored automatically
- **Lap telemetry charts** — speed (GPS & OBD), throttle, brake, RPM, lateral/longitudinal G plotted on a distance axis
- **GPS track map** — Leaflet map rendered from on-board GPS data
- **Lap comparison** — overlay multiple laps on the same distance axis; Delta-T chart shows time gained/lost vs reference lap
- **My Cars** — maintain a garage with performance specs (power, weight, drivetrain, engine)
- **Track directory** — public track list with best-lap GPS map per configuration
- **Leaderboard** — fastest public laps per track configuration
- **Authentication** — local accounts with JWT + refresh tokens; Google and GitHub OAuth supported
- **Admin panel** — user management, track editing

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI |
| Database | PostgreSQL 16 (production) · SQLite (tests) |
| ORM / migrations | SQLAlchemy 2.0 · Alembic |
| Frontend | Jinja2 templates · vanilla JS |
| Maps | Leaflet.js |
| Charts | Chart.js 4 |
| Containers | Docker · Docker Compose |

---

## Quick start (local development)

### Prerequisites

- Docker and Docker Compose
- Python 3.12 (only needed for running tests without Docker)

### 1. Clone and configure

```bash
git clone <repo-url>
cd racetrace
cp .env.development.example .env.development
```

The default `.env.development` values work out of the box — no edits needed for local dev.

### 2. Start services

```bash
docker compose up
```

This starts PostgreSQL, Redis, and the FastAPI app with live reload on **http://localhost:8000**.

### 3. Run migrations

```bash
docker compose exec app alembic upgrade head
```

### 4. Seed sample data (optional)

Place a TrackAddict CSV at `uploads/sample-session.csv`, then:

```bash
docker compose exec app python scripts/seed.py
```

This creates an admin user (`antonio` / `racetrace`) and imports the sample session.

---

## Running tests

Tests use an in-memory SQLite database — no running services required.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install dependencies (first time)
pip install -r requirements.txt

# Run all tests
pytest tests/
```

All 41 tests should pass in ~14 seconds.

---

## Environments

Three environments are supported. Each has its own env file and Docker Compose file.

| Environment | Compose file | Env file |
|---|---|---|
| Development | `docker-compose.yml` | `.env.development` |
| Testing | `docker-compose.testing.yml` | `.env.testing` |
| Production | `docker-compose.prod.yml` | `.env.production` |

### Setting up a new server (testing or production)

```bash
# Copy the template for your environment
cp .env.testing.example .env.testing      # or .env.production.example

# Edit the file — set database password, secret key, domain
nano .env.testing

# Start all services
docker compose -f docker-compose.testing.yml up -d

# Run migrations
APP_ENV=testing alembic upgrade head
```

Key differences per environment:

| Setting | Development | Testing | Production |
|---|---|---|---|
| `DEBUG` | `true` | `false` | `false` |
| Uvicorn | `--reload` (1 worker) | 2 workers | 4 workers |
| DB port | exposed on 5432 | internal only | internal only |
| Token TTL | 1440 min | 60 min | 15 min |

### Generating a secret key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Database migrations

Alembic reads `DATABASE_URL` from the active environment settings automatically.

```bash
# Apply all pending migrations
APP_ENV=production alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe the change"

# Roll back one migration
APP_ENV=production alembic downgrade -1
```

For a fresh database without Alembic (bare SQL):

```bash
psql -U racetrace -d racetrace -f docs/schema_create.sql
```

---

## Project structure

```
racetrace/
├── app/
│   ├── api/v1/          # FastAPI routers (auth, sessions, laps, cars, tracks, admin…)
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/
│   │   ├── session_importer.py      # file → database pipeline
│   │   └── telemetry/
│   │       ├── parser.py            # TrackAddict CSV parser
│   │       └── comparator.py        # distance-based lap comparison
│   ├── templates/       # Jinja2 HTML templates
│   └── config.py        # settings loaded from .env.{APP_ENV}
├── alembic/             # database migrations
├── tests/               # pytest suite (41 tests)
├── scripts/seed.py      # local dev seed data
├── docs/
│   ├── SYSTEM.md        # full architecture reference
│   ├── schema_create.sql
│   └── schema_drop.sql
├── docker-compose.yml           # development
├── docker-compose.testing.yml   # testing server
└── docker-compose.prod.yml      # production server
```

See [docs/SYSTEM.md](docs/SYSTEM.md) for the full architecture reference including the data model, API endpoints, and telemetry pipeline.

---

## Supported data formats

| Format | Source app | Status |
|---|---|---|
| TrackAddict CSV | TrackAddict (iOS/Android) | Supported |
| MoTeC LD | MoTeC i2 | Planned |
| AiM DRK/XDRK | AiM Race Studio | Planned |

---

## Default accounts

After running `scripts/seed.py`:

| Username | Password | Role |
|---|---|---|
| `antonio` | `racetrace` | Admin |

Create additional users via the Register page or the API.
