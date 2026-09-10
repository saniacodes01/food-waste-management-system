from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://foodwaste:password@localhost:5432/foodwaste_db"
    # optional: keep every table inside one named schema (handy when you can't
    # CREATE DATABASE on a shared server). Empty = use the default schema.
    db_schema: str = ""
    secret_key: str = "change-this-secret-key"
    allowed_origins: str = "http://localhost:5173"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"
    match_radius_km: float = 25.0

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
