"""Turn a Gmail messages.get JSON payload into AlertRecord + attachments. No Google SDK."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from finsca.ingest.alerts import AlertRecord

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class AttachmentRef:
    filename: str
    data: bytes | None
    attachment_id: str | None


@dataclass(frozen=True)
class GmailPull:
    record: AlertRecord
    message_id: str
    attachments: tuple[AttachmentRef, ...]


def decode_gmail_message(payload: dict) -> GmailPull:
    headers = {item["name"].lower(): item["value"] for item in payload.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    sender = headers.get("from", "")
    sent_at = _parse_date(headers.get("date"))
    body = _plain_text(payload.get("payload") or {})
    blob = f"{subject}\n{body}".strip() if subject else body
    attachments = tuple(_attachments(payload.get("payload") or {}))
    return GmailPull(
        record=AlertRecord(body=blob, address=sender, sent_at=sent_at),
        message_id=str(payload.get("id") or "unknown"),
        attachments=attachments,
    )


def safe_stem(message_id: str, sender: str) -> str:
    who = _SAFE.sub("_", sender.split("<")[-1].split(">")[0])[:40]
    return f"{message_id[:12]}_{who or 'mail'}"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _plain_text(part: dict) -> str:
    mime = part.get("mimeType") or ""
    data = part.get("body", {}).get("data")
    if mime.startswith("text/plain") and data:
        return _b64(data)
    chunks: list[str] = []
    for child in part.get("parts") or []:
        text = _plain_text(child)
        if text:
            chunks.append(text)
    if chunks:
        return "\n".join(chunks)
    if mime.startswith("text/html") and data:
        return _strip_html(_b64(data))
    return ""


def _attachments(part: dict) -> list[AttachmentRef]:
    found: list[AttachmentRef] = []
    if _is_pdf_part(part):
        body = part.get("body") or {}
        data = body.get("data")
        found.append(
            AttachmentRef(
                filename=part.get("filename") or "statement.pdf",
                data=base64.urlsafe_b64decode(data + "==") if data else None,
                attachment_id=body.get("attachmentId"),
            )
        )
    for child in part.get("parts") or []:
        found.extend(_attachments(child))
    return found


def _is_pdf_part(part: dict) -> bool:
    name = (part.get("filename") or "").lower()
    mime = (part.get("mimeType") or "").lower()
    if name.endswith(".pdf") or mime == "application/pdf":
        return True
    return mime == "application/octet-stream" and name.endswith(".pdf")


def _b64(data: str) -> str:
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def _strip_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", " ", raw)
