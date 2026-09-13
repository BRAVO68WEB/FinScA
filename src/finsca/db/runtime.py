from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from finsca.config.settings import Settings
from finsca.db.engine import init_db, make_engine
from finsca.db.session import session_scope


@contextmanager
def db_session() -> Iterator[Session]:
    settings = Settings()
    settings.ensure_dirs()
    engine = make_engine(settings.db_path)
    init_db(engine)
    with session_scope(engine) as session:
        yield session
