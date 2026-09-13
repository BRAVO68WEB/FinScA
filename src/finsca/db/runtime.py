from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from finsca.config.settings import Settings
from finsca.db.engine import make_engine
from finsca.db.session import session_scope


@contextmanager
def db_session() -> Iterator[Session]:
    settings = Settings()
    settings.ensure_dirs()
    with session_scope(make_engine(settings.db_path)) as session:
        yield session
