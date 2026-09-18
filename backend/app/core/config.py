"""Configuración por entorno (12-factor). Ningún secreto vive en el código."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://ecoumb:ecoumb@localhost:5432/ecoumb"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_private_key: str | None = None
    jwt_public_key: str | None = None
    jwt_issuer: str = "ecoumb"
    jwt_audience: str = "ecoumb-api"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    bcrypt_rounds: int = 12
    auth_rate_limit_per_minute: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _validate_production_requirements(self) -> Self:
        if self.is_production and not (self.jwt_private_key and self.jwt_public_key):
            raise ValueError("JWT_PRIVATE_KEY y JWT_PUBLIC_KEY son obligatorias en producción")
        if self.is_production and "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS no puede ser '*' en producción")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
