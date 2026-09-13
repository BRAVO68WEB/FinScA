from __future__ import annotations

import hashlib
import uuid


def new_id() -> str:
    return uuid.uuid4().hex


def content_hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()
