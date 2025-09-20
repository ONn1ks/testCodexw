from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RateLimitConfig(BaseModel):
    harbor_per_min: int = Field(30, description="Allowed Harbor API requests per minute")
    mrkt_per_min: int = Field(20, description="Allowed MRKT backend requests per minute")
    palace_per_min: int = Field(20, description="Allowed Palace backend requests per minute")
    pixel_per_min: int = Field(20, description="Allowed Pixel backend requests per minute")


class AlertConfig(BaseModel):
    min_interval_sec: int = Field(60, ge=0)
    same_event_cooldown_sec: int = Field(600, ge=0)
    under_floor_pct: float = Field(7.0, ge=0.0)
    depth_delta_pct: float = Field(5.0, ge=0.0)
    thin_floor_min_lots: int = Field(5, ge=0)


class DigestConfig(BaseModel):
    enabled: bool = True
    times: list[str] = Field(default_factory=lambda: ["10:00", "20:00"])

    @field_validator("times")
    @classmethod
    def _validate_times(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            hour, minute = value.split(":", 1)
            if not (hour.isdigit() and minute.isdigit()):
                raise ValueError("Digest time must be HH:MM")
            h, m = int(hour), int(minute)
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError("Digest time must be within 00:00-23:59")
            cleaned.append(f"{h:02d}:{m:02d}")
        return sorted(dict.fromkeys(cleaned))


class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")
    db_dsn: str = Field(..., env="DB_DSN")
    redis_dsn: str = Field(..., env="REDIS_DSN")
    timezone: str = Field("Europe/Amsterdam", env="TZ")

    whitelist_ids: set[int] = Field(default_factory=set, env="WHITELIST_IDS")

    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    digest: DigestConfig = Field(default_factory=DigestConfig)

    harbor_api_url: str = Field("https://api.harbor.gg", env="HARBOR_API_URL")

    webhook_url: str | None = Field(None, env="WEBHOOK_URL")
    webhook_path: str = Field("/webhook", env="WEBHOOK_PATH")
    webhook_secret: str | None = Field(None, env="WEBHOOK_SECRET")
    run_scheduler: bool = Field(True, env="RUN_SCHEDULER")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("whitelist_ids", mode="before")
    @classmethod
    def _parse_whitelist(cls, value: str | set[int] | None) -> set[int]:
        if value is None:
            return set()
        if isinstance(value, set):
            return value
        ids = set()
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            ids.add(int(item))
        return ids


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["AlertConfig", "DigestConfig", "RateLimitConfig", "Settings", "get_settings"]
