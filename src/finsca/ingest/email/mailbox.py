from __future__ import annotations

import mailbox
import tempfile
import zipfile
from datetime import datetime, timezone
from email import message_from_bytes, policy
from email.message import Message
from pathlib import Path

from finsca.ingest.alerts import AlertRecord
from finsca.ingest.errors import ParseError


def load_email(path: Path) -> list[AlertRecord]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".eml":
            return [_from_message(message_from_bytes(path.read_bytes(), policy=policy.default))]
        if suffix == ".mbox":
            return [_from_message(msg) for msg in mailbox.mbox(str(path))]
        if suffix == ".zip":
            return _from_zip(path)
        raise ParseError(f"unsupported email dump: {path.suffix}")
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(f"could not read email dump: {exc}") from exc


def _from_zip(path: Path) -> list[AlertRecord]:
    records: list[AlertRecord] = []
    with zipfile.ZipFile(path) as bundle:
        for name in bundle.namelist():
            lower = name.lower()
            if lower.endswith(".eml"):
                msg = message_from_bytes(bundle.read(name), policy=policy.default)
                records.append(_from_message(msg))
            elif lower.endswith(".mbox"):
                extracted = bundle.read(name)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mbox") as handle:
                    handle.write(extracted)
                    tmp = Path(handle.name)
                try:
                    records.extend(_from_message(msg) for msg in mailbox.mbox(str(tmp)))
                finally:
                    tmp.unlink(missing_ok=True)
    return records


def _from_message(msg: Message) -> AlertRecord:
    subject = str(msg.get("Subject") or "").strip()
    body = _plain_body(msg)
    blob = f"{subject}\n{body}".strip() if subject else body
    return AlertRecord(
        body=blob,
        address=str(msg.get("From") or ""),
        sent_at=_msg_date(msg),
    )


def _plain_body(msg: Message) -> str:
    if msg.is_multipart():
        parts: list[str] = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_content()
                if isinstance(payload, str):
                    parts.append(payload)
        return "\n".join(parts)
    payload = msg.get_content()
    return payload if isinstance(payload, str) else ""


def _msg_date(msg: Message) -> datetime | None:
    raw = msg.get("Date")
    if not raw:
        return None
    try:
        from email.utils import parsedate_to_datetime

        value = parsedate_to_datetime(raw)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None
