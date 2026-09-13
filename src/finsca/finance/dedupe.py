"""Cross-source same-event identity: account + date + signed amount."""

from datetime import date, datetime
from decimal import Decimal

from finsca.core.money import to_paise


def event_fingerprint(account_id: str, posted_at: datetime, amount: Decimal) -> tuple[str, str, int]:
    day = posted_at.date() if isinstance(posted_at, datetime) else posted_at
    if not isinstance(day, date):
        raise TypeError("posted_at must be a datetime or date")
    return (account_id, day.isoformat(), to_paise(amount))
