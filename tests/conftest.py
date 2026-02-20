import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Shared helpers ──────────────────────────────────────────────────────────

def make_user(client, username, password="pass123"):
    """Register and return an access token."""
    client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
    })
    res = client.post("/api/v1/auth/login", data={
        "username": username,
        "password": password,
    })
    return res.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def seed_track_config(db):
    """Insert a Track + TrackConfiguration and return the config id."""
    from app.models.track import Track
    from app.models.track_configuration import TrackConfiguration

    track = Track(name="Test Circuit", country="Testland")
    db.add(track)
    db.flush()
    config = TrackConfiguration(
        track_id=track.id,
        name="Main Layout",
        length_meters=3200,
        num_sectors=3,
        is_default=True,
    )
    db.add(config)
    db.commit()
    return config.id
