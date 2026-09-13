from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from finsca.cli.app import app

runner = CliRunner()


def test_accounts_add_then_list(data_dir: Path) -> None:
    added = runner.invoke(
        app,
        [
            "accounts",
            "add",
            "HDFC Salary",
            "--type",
            "savings",
            "--institution",
            "HDFC",
            "--last4",
            "4521",
        ],
    )
    assert added.exit_code == 0, added.output
    assert "HDFC Salary" in added.output
    listed = runner.invoke(app, ["accounts", "list"])
    assert listed.exit_code == 0, listed.output
    assert "4521" in listed.output
    assert "HDFC Salary" in listed.output


def test_accounts_alias_and_months(data_dir: Path) -> None:
    runner.invoke(
        app,
        ["accounts", "add", "HDFC Salary", "--type", "savings", "--last4", "4521"],
    )
    aliased = runner.invoke(app, ["accounts", "alias", "4521", "salary a/c"])
    assert aliased.exit_code == 0, aliased.output
    seeded = runner.invoke(
        app,
        [
            "accounts",
            "months",
            "set",
            "4521",
            "--month",
            "2026-08",
            "--opening",
            "10000",
            "--closing",
            "12500.50",
        ],
    )
    assert seeded.exit_code == 0, seeded.output
    months = runner.invoke(app, ["accounts", "months", "--account", "4521", "--month", "2026-08"])
    assert months.exit_code == 0, months.output
    assert "2026-08" in months.output
    assert "12500.50" in months.output
