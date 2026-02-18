"""
Seed the local database with:
  - Admin user: antonio / password: racetrace
  - Track: La Pista (Colombia)
  - TrackConfiguration derived from the sample file GPS endpoint
  - Session + all laps imported from uploads/sample-session.csv
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.chdir(os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.user import User
from app.models.track import Track
from app.models.track_configuration import TrackConfiguration
from app.models.session import Session, SessionType
from app.models.lap import Lap
from app.core.security import hash_password
from app.services.session_importer import import_session_laps

db = SessionLocal()

# ── User ──────────────────────────────────────────────────────────────────
existing = db.query(User).filter(User.username == "antonio").first()
if existing:
    user = existing
    print(f"User 'antonio' already exists (id={user.id}), reusing.")
else:
    user = User(
        username="antonio",
        email="ajalvareze@gmail.com",
        full_name="Antonio",
        hashed_password=hash_password("racetrace"),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created user: {user.username} (id={user.id})")

# ── Track ─────────────────────────────────────────────────────────────────
track = db.query(Track).filter(Track.name == "La Pista").first()
if not track:
    track = Track(name="La Pista", country="Colombia", city="Tocancipá")
    db.add(track)
    db.flush()
    config = TrackConfiguration(
        track_id=track.id,
        name="Main Circuit",
        num_sectors=3,
        start_finish_lat=4.961152,
        start_finish_lon=-73.947248,
        is_default=True,
    )
    db.add(config)
    db.commit()
    db.refresh(track)
    print(f"Created track: {track.name} (id={track.id}), config id={config.id}")
else:
    config = track.configurations[0]
    print(f"Track '{track.name}' already exists (id={track.id}).")

# ── Session ───────────────────────────────────────────────────────────────
sample_file = os.path.join("uploads", "sample-session.csv")
if not os.path.exists(sample_file):
    print(f"Sample file not found at {sample_file}. Skipping session import.")
    sys.exit(0)

existing_session = db.query(Session).filter(
    Session.user_id == user.id,
    Session.source_file_path.like("%sample-session%"),
).first()

if existing_session:
    print(f"Session already imported (id={existing_session.id}).")
else:
    import shutil
    dest_dir = os.path.join("uploads", "sessions", "seed")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "sample-session.csv")
    shutil.copy2(sample_file, dest)

    session = Session(
        user_id=user.id,
        track_configuration_id=config.id,
        session_type=SessionType.practice,
        date=datetime(2025, 6, 10, 14, 0, tzinfo=timezone.utc),
        notes="Imported from sample TrackAddict file",
        is_public=True,
        source_file_path=dest,
        app_source="trackaddict",
        vehicle_hint="Renault",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    print(f"Created session id={session.id}, importing laps…")

    import_session_laps(session.id, dest, "csv")

    lap_count = db.query(Lap).filter(Lap.session_id == session.id).count()
    best = (
        db.query(Lap)
        .filter(Lap.session_id == session.id, Lap.is_valid == True)  # noqa: E712
        .order_by(Lap.lap_time_ms)
        .first()
    )
    print(f"Laps imported: {lap_count}")
    if best and best.lap_time_ms:
        ms = best.lap_time_ms
        print(f"Best lap: {ms // 60000}:{(ms % 60000) / 1000:06.3f}  (lap #{best.lap_number}, max speed {best.max_speed_kmh} km/h)")

db.close()
print("\nSeed complete.")
print("Login at http://localhost:8000/login")
print("  username: antonio")
print("  password: racetrace")
