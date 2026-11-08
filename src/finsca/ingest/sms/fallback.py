"""Compact-model parse for one alert the templates miss."""

from __future__ import annotations

from decimal import InvalidOperation
from typing import Any, Callable

from finsca.core.money import parse_inr
from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.patterns import posted_at
from finsca.ingest.types import ParsedLine
from finsca.llm.redaction import redact
from finsca.llm.router import LLMRouter

CompleteFn = Callable[[list[dict[str, str]]], dict[str, Any] | None]

SMS_FALLBACK_SYSTEM = (
    "Extract one Indian bank debit or credit alert. "
    'Return JSON: {"posted_at": "YYYY-MM-DD", "amount": "-10.00", '
    '"description": "MERCHANT", "last4": "4521", "institution": "HDFC"}. '
    "Amount is a signed decimal string, debit negative. "
    "If this is not a transaction alert, return {}."
)


def parse_unmatched(
    body: str,
    *,
    address: str = "",
    complete: CompleteFn | None = None,
) -> ParsedLine | None:
    fn = complete if complete is not None else _compact_complete()
    if fn is None:
        return None
    user = redact(f"{address}\n{body}" if address else body)
    try:
        payload = fn(
            [
                {"role": "system", "content": SMS_FALLBACK_SYSTEM},
                {"role": "user", "content": user},
            ]
        )
    except Exception:
        return None
    if not isinstance(payload, dict) or "posted_at" not in payload or "amount" not in payload:
        return None
    description = str(payload.get("description") or "").strip()
    last4 = str(payload.get("last4") or "").strip()
    if not description or len(last4) < 4:
        return None
    try:
        amount = parse_inr(payload["amount"])
        when = posted_at(str(payload["posted_at"]))
    except (InvalidOperation, ValueError, TypeError, IndexError, ArithmeticError):
        return None
    institution = payload.get("institution")
    return ParsedLine(
        posted_at=when,
        amount=amount,
        description=description,
        channel=infer_channel(description),
        last4=last4[-4:],
        institution=str(institution) if institution else None,
    )


def _compact_complete() -> CompleteFn | None:
    router = LLMRouter()
    if router.provider_for("compact") is None:
        return None

    def call(messages: list[dict[str, str]]) -> dict[str, Any] | None:
        parsed = router.complete("compact", messages)
        return parsed if isinstance(parsed, dict) else None

    return call
