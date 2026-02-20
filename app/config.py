import os
from functools import lru_cache
from pydantic_settings import BaseSettings

# Selects which .env.* file to load when running outside Docker.
# In Docker the env file is injected by docker-compose via env_file:,
# so APP_ENV is only needed for bare uvicorn / alembic runs on the host.
_app_env = os.getenv("APP_ENV", "development")


class Settings(BaseSettings):
    app_env: str = _app_env
    app_name: str = "RaceTrace"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://racetrace:racetrace@localhost:5432/racetrace"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    admin_token_expire_minutes: int = 120

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8000"

    # File storage
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 50
    allowed_telemetry_extensions: list[str] = [".csv", ".json", ".ld", ".drk", ".xdrk"]

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = f".env.{_app_env}"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
