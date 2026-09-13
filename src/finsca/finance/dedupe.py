"""One event identity: account + calendar date + signed paise."""

from datetime import datetime
from decimal import Decimal

from finsca.core.ids import content_hash
from finsca.core.money import to_paise


def event_fingerprint(account_id: str, posted_at: datetime, amount: Decimal) -> tuple[str, str, int]:
    return (account_id, posted_at.date().isoformat(), to_paise(amount))


def event_hash(account_id: str, posted_at: datetime, amount: Decimal) -> str:
    account, day, paise = event_fingerprint(account_id, posted_at, amount)
    return content_hash(account, day, str(paise))
