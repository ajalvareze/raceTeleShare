# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the development server
```bash
uvicorn app.main:app --reload
```

### Run tests
```bash
pytest                        # all tests
pytest tests/test_auth.py     # single file
pytest -k "test_register"     # single test by name
```
Tests use SQLite in-memory (via `tests/conftest.py`) — no running Postgres needed.

### Database migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Docker (full stack: app + Postgres + Redis)
```bash
cp .env.example .env
docker compose up -d
docker compose exec app alembic upgrade head
```

## Architecture

### Request flow
```
HTTP request
  → app/main.py              (FastAPI app, CORS, mounts)
  → app/api/v1/router.py     (aggregates all API routers)
  → app/api/v1/<resource>.py (route handler)
  → app/api/deps.py          (auth: JWT decode → User lookup)
  → app/services/            (business logic)
  → app/models/              (SQLAlchemy ORM, written via db session)
```

HTML pages are served by `app/api/v1/web.py` (Jinja2 templates). The frontend fetches data from the JSON API using `fetch()` with a JWT stored in `localStorage`. Auth headers are injected via `authHeaders()` defined in `app/templates/base.html`.

### Data model hierarchy
```
User
 └── Car (owned by user)
 └── Session (track + car + date + type)
      └── Lap (lap number, times, telemetry file ref, derived metrics)
```

`Session.is_public` controls visibility — private sessions are only accessible to their owner.

### Telemetry pipeline
1. `POST /api/v1/laps/{id}/upload` saves the file via `app/services/storage.py`
2. A FastAPI `BackgroundTask` calls `app/services/telemetry/processor.py` which parses the file and writes derived metrics (max speed, avg speed, throttle/brake peaks, per-channel summary JSON) back to the `Lap` row.
3. `POST /api/v1/laps/compare` calls `app/services/telemetry/comparator.py` which resamples all channels to the reference lap's time axis (numpy linear interpolation) and computes cumulative delta-T.

### Telemetry parser contract
Every parser in `app/services/telemetry/parser.py` must return:
```python
{
    "channels": {
        "<name>": {"unit": str|None, "timestamps": list[float], "data": list[float]}
    },
    "sample_rate_hz": float | None,
    "lap_time_ms": int | None,
}
```
CSV: first column is the time axis (seconds). JSON: must match the structure above. MoTeC `.ld` and AiM `.drk`/`.xdrk` are stubs that raise `NotImplementedError`.

### Settings
All configuration lives in `app/config.py` (Pydantic `BaseSettings`, reads `.env`). The singleton is accessed via `get_settings()` which is LRU-cached. Never instantiate `Settings` directly.

### Auth
`app/core/security.py` — bcrypt password hashing, HS256 JWT tokens.
`app/api/deps.py` — `get_current_user` dependency (Bearer token → User). `get_current_superuser` gates track creation/editing.
