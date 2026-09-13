"""Gmail API: OAuth readonly + pull bank-alert mail into the inbox."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from finsca.config.settings import Settings
from finsca.ingest.email.gmail_decode import AttachmentRef, decode_gmail_message, safe_stem

SCOPE = ("https://www.googleapis.com/auth/gmail.readonly",)
# Gmail has no *@*.bank.in regex; from:bank.in matches yes.bank.in, axis.bank.in, etc.
BANK_FILTER = (
    "from:(bank.in OR sbicard.com OR hdfcbank.net OR hdfcbank.com "
    "OR icicibank.com OR axisbank.com OR idfcfirstbank.com "
    "OR sbi.co.in OR onlinesbi.com OR kotak.com "
    "OR cred.club OR protect@cred.club "
    "OR phonepe.com OR google.com OR paytm.com "
    "OR yes.bank.in OR axis.bank.in OR hdfcbank.bank.in OR idfcfirst.bank.in "
    "OR estatement@yes.bank.in OR statements@axis.bank.in OR alerts@axis.bank.in "
    "OR Emailstatements.cards@hdfcbank.bank.in OR statement@idfcfirst.bank.in "
    "OR PRIME.card@sbicard.com)"
    " OR subject:(debited OR credited OR spent OR EMI OR statement OR estatement "
    "OR e-statement OR \"credit card\" OR bill OR OTP)"
)
_PACE_SECONDS = 0.4
_RETRY_ATTEMPTS = 8


@dataclass(frozen=True)
class GmailPullResult:
    emails: int
    pdfs: int
    skipped: int


def credentials_path(settings: Settings) -> Path:
    return settings.data_dir / "gmail_credentials.json"


def token_path(settings: Settings) -> Path:
    return settings.data_dir / "gmail_token.json"


def seen_path(settings: Settings) -> Path:
    return settings.data_dir / "gmail_seen.json"


def login(settings: Settings) -> Path:
    creds_file = credentials_path(settings)
    if not creds_file.exists():
        raise FileNotFoundError(
            f"Put a Google OAuth desktop client JSON at {creds_file} "
            "(Google Cloud → APIs → Gmail API → OAuth client → Desktop app)."
        )
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), list(SCOPE))
    creds = flow.run_local_server(port=0)
    dest = token_path(settings)
    dest.write_text(creds.to_json(), encoding="utf-8")
    return dest


def search_query(*, months: int, extra: str | None = None) -> str:
    if months < 1:
        raise ValueError("months must be >= 1")
    body = (extra or BANK_FILTER).strip()
    if _has_time_bound(body):
        return body
    return f"newer_than:{months}m ({body})"


def _has_time_bound(query: str) -> bool:
    return bool(re.search(r"\b(newer_than|older_than|after|before):", query, re.I))


def pull(
    settings: Settings,
    *,
    query: str | None = None,
    months: int = 1,
    max_results: int = 200,
) -> GmailPullResult:
    service = _service(settings)
    q = search_query(months=months, extra=query or settings.gmail_query)
    ids = _list_ids(service, q, max_results)
    settings.ensure_dirs()
    seen = load_seen(settings)
    emails = pdfs = skipped = 0
    for message_id in ids:
        if _already_pulled(message_id, seen):
            skipped += 1
            continue
        raw = _execute(service.users().messages().get(userId="me", id=message_id, format="full"))
        pulled = decode_gmail_message(raw)
        stem = safe_stem(pulled.message_id, pulled.record.address)
        eml = settings.inbox_dir / "email" / f"{stem}.eml"
        eml.write_text(_as_eml(pulled.record), encoding="utf-8")
        emails += 1
        for ref in pulled.attachments:
            blob = _attachment_bytes(service, message_id, ref)
            if blob is None:
                continue
            dest = settings.inbox_dir / "pdf" / f"{stem}_{Path(ref.filename).name}"
            dest.write_bytes(blob)
            pdfs += 1
        seen.add(message_id)
        save_seen(settings, seen)
    return GmailPullResult(emails=emails, pdfs=pdfs, skipped=skipped)


def load_seen(settings: Settings) -> set[str]:
    dest = seen_path(settings)
    ids: set[str] = set()
    if dest.exists():
        payload = json.loads(dest.read_text(encoding="utf-8"))
        ids.update(payload.get("ids", []))
    for folder in (settings.inbox_dir / "email", settings.archive_dir):
        if not folder.exists():
            continue
        for path in folder.rglob("*.eml"):
            prefix = path.name.split("_", 1)[0]
            if len(prefix) >= 8:
                ids.add(prefix)
    return ids


def _already_pulled(message_id: str, seen: set[str]) -> bool:
    return message_id in seen or message_id[:12] in seen


def save_seen(settings: Settings, ids: set[str]) -> None:
    seen_path(settings).write_text(json.dumps({"ids": sorted(ids)}, indent=2), encoding="utf-8")


def _attachment_bytes(service, message_id: str, ref: AttachmentRef) -> bytes | None:
    if ref.data:
        return ref.data
    if not ref.attachment_id:
        return None
    raw = _execute(
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=ref.attachment_id)
    )
    data = raw.get("data")
    if not data:
        return None
    import base64

    return base64.urlsafe_b64decode(data + "==")


def _execute(request, *, attempts: int = _RETRY_ATTEMPTS):
    delay = 1.0
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            result = request.execute()
            time.sleep(_PACE_SECONDS)
            return result
        except Exception as exc:
            last = exc
            if not _is_rate_limit(exc) or attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise last or RuntimeError("gmail request failed")


def _is_rate_limit(exc: BaseException) -> bool:
    code = getattr(getattr(exc, "resp", None), "status", None)
    text = str(exc).lower()
    return code in {403, 429} and any(token in text for token in ("ratelimit", "rate limit", "quota", "usagelimits"))


def _service(settings: Settings):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    dest = token_path(settings)
    if not dest.exists():
        raise FileNotFoundError("Not logged in. Run: finsca gmail login")
    creds = Credentials.from_authorized_user_file(str(dest), list(SCOPE))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        dest.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def _list_ids(service, query: str, max_results: int) -> list[str]:
    ids: list[str] = []
    token = None
    while len(ids) < max_results:
        page = _execute(
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=token, maxResults=min(100, max_results - len(ids)))
        )
        ids.extend(item["id"] for item in page.get("messages") or [])
        token = page.get("nextPageToken")
        if not token:
            break
    return ids


def _as_eml(record) -> str:
    when = record.sent_at.strftime("%a, %d %b %Y %H:%M:%S %z") if record.sent_at else ""
    return f"From: {record.address}\nDate: {when}\n\n{record.body}\n"
