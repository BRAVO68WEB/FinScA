from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FINSCA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("data"))
    reasoning_provider: Literal["grok", "openai"] = "grok"
    compact_provider: Literal["openai", "grok"] = "openai"
    grok_model: str = "grok-4-5"
    openai_model: str = "gpt-4.1"
    compact_model: str = "gpt-4.1-mini"
    label_min_confidence: float = 0.7
    self_transfer_window_hours: int = 72
    llm_off: bool = False
    gmail_query: str | None = None

    @property
    def inbox_dir(self) -> Path:
        return self.data_dir / "inbox"

    @property
    def archive_dir(self) -> Path:
        return self.data_dir / "archive"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "finsca.db"

    def ensure_dirs(self) -> None:
        for path in (
            self.inbox_dir / "pdf",
            self.inbox_dir / "email",
            self.inbox_dir / "sms",
            self.archive_dir,
            self.reports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
