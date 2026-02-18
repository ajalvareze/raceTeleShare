from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
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
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
