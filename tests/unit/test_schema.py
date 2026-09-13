from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from finsca.db.engine import init_db, make_engine


def test_init_db_creates_core_tables(data_dir: Path) -> None:
    engine = make_engine(data_dir / "finsca.db")
    init_db(engine)
    names = set(inspect(engine).get_table_names())
    assert {
        "accounts",
        "account_months",
        "transactions",
        "loans",
        "emi_occurrences",
        "rules",
        "ingest_runs",
        "ingest_files",
    } <= names
