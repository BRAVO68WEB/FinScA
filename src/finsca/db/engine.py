from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine

from finsca.db.schema import Base

_engines: dict[str, Engine] = {}


def make_engine(db_path: Path) -> Engine:
    key = str(db_path.resolve())
    cached = _engines.get(key)
    if cached is not None:
        return cached
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    init_db(engine)
    _engines[key] = engine
    return engine


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
