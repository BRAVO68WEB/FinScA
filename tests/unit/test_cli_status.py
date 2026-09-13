from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from finsca.cli.app import app

runner = CliRunner()


def test_default_command_says_no_runs_yet(data_dir: Path) -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0, result.output
    assert "no runs yet" in result.output.lower()
    assert "pdf=0" in result.output
    assert "email=0" in result.output
    assert "sms=0" in result.output
    assert "pending reviews" in result.output.lower()
