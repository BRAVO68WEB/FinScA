"""Gmail API: OAuth readonly + pull bank-alert mail into the inbox."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from finsca.config.settings import Settings
from finsca.ingest.email.gmail_decode import decode_gmail_message, safe_stem

SCOPE = ("https://www.googleapis.com/auth/gmail.readonly",)
BANK_FILTER = (
    "from:(hdfcbank.net OR icicibank.com OR axisbank.com OR idfcfirstbank.com "
    "OR sbi.co.in OR onlinesbi.com OR kotak.com OR cred.club OR phonepe.com "
    "OR google.com OR paytm.com)"
    " OR subject:(debited OR credited OR spent OR EMI OR statement OR OTP)"
)


@dataclass(frozen=True)
class GmailPullResult:
    emails: int
    pdfs: int


def credentials_path(settings: Settings) -> Path:
    return settings.data_dir / "gmail_credentials.json"


def token_path(settings: Settings) -> Path:
    return settings.data_dir / "gmail_token.json"


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
    emails = pdfs = 0
    for message_id in ids:
        raw = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        pulled = decode_gmail_message(raw)
        stem = safe_stem(pulled.message_id, pulled.record.address)
        eml = settings.inbox_dir / "email" / f"{stem}.eml"
        eml.write_text(_as_eml(pulled.record), encoding="utf-8")
        emails += 1
        for name, blob in pulled.attachments:
            dest = settings.inbox_dir / "pdf" / f"{stem}_{Path(name).name}"
            dest.write_bytes(blob)
            pdfs += 1
    return GmailPullResult(emails=emails, pdfs=pdfs)


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
        page = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=token, maxResults=min(100, max_results - len(ids)))
            .execute()
        )
        ids.extend(item["id"] for item in page.get("messages") or [])
        token = page.get("nextPageToken")
        if not token:
            break
    return ids


def _as_eml(record) -> str:
    when = record.sent_at.strftime("%a, %d %b %Y %H:%M:%S %z") if record.sent_at else ""
    return f"From: {record.address}\nDate: {when}\n\n{record.body}\n"
