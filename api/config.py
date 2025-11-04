"""Application configuration helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "Tech Challenge Books API"
    api_prefix: str = "/api/v1"
    version: str = "1.0.0"
    description: str = (
        "Public dataset API exposing the catalogue scraped from books.toscrape.com "
        "for data science and machine learning experimentation."
    )
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.joinpath("data")
    )
    csv_filename: str = "books_raw.csv"
    db_filename: str = "books.db"
    rebuild_db_on_startup: bool = False
    default_page_size: int = 50
    max_page_size: int = 200

    model_config = SettingsConfigDict(
        env_prefix="BOOKS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def csv_path(self) -> Path:
        """Return the fully qualified path to the scraped CSV file."""

        return self.data_dir.joinpath(self.csv_filename).resolve()

    @property
    def db_path(self) -> Path:
        """Return the fully qualified path to the SQLite database."""

        return self.data_dir.joinpath(self.db_filename).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""

    settings = Settings()  # type: ignore[call-arg]
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings


def override_settings(**kwargs: Any) -> Settings:
    """Utility used in tests to override selective configuration values."""

    data = Settings().model_dump()
    data.update(kwargs)
    override = Settings(**data)
    override.data_dir.mkdir(parents=True, exist_ok=True)
    return override
