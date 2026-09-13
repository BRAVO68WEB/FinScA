from __future__ import annotations

from pathlib import Path

from finsca.config.settings import Settings


def test_settings_default_paths_under_data_dir(data_dir: Path) -> None:
    settings = Settings()
    assert settings.data_dir == data_dir
    assert settings.inbox_dir == data_dir / "inbox"
    assert settings.archive_dir == data_dir / "archive"
    assert settings.reports_dir == data_dir / "reports"
    assert settings.db_path == data_dir / "finsca.db"


def test_settings_default_providers() -> None:
    settings = Settings()
    assert settings.reasoning_provider == "grok"
    assert settings.compact_provider == "openai"
    assert settings.llm_off is False
    assert settings.label_min_confidence == 0.7
    assert settings.self_transfer_window_hours == 72
