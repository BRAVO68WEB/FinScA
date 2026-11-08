"""Last-resort statement extract. Bank and card parsers run first."""

from __future__ import annotations

from decimal import InvalidOperation
from typing import Any, Callable

from finsca.core.enums import AccountType
from finsca.core.money import parse_inr
from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.header import account_display_name, parse_header
from finsca.ingest.pdf.patterns import posted_at
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine
from finsca.llm.prompts.parse_unknown import PARSE_UNKNOWN_SYSTEM
from finsca.llm.redaction import redact
from finsca.llm.router import LLMRouter

CompleteFn = Callable[[list[dict[str, str]]], dict[str, Any] | None]


def parse_unknown_statement(
    text: str,
    *,
    filename: str = "",
    complete: CompleteFn | None = None,
) -> ParsedBatch | None:
    fn = complete if complete is not None else _compact_complete()
    if fn is None:
        return None
    user = redact(f"{filename}\n{text}" if filename else text)
    try:
        payload = fn(
            [
                {"role": "system", "content": PARSE_UNKNOWN_SYSTEM},
                {"role": "user", "content": user},
            ]
        )
    except Exception:
        return None
    lines = _lines(payload)
    if not lines:
        return None
    header = parse_header(text)
    last4 = next((line.last4 for line in lines if line.last4), None) or header.last4
    if not last4:
        return None
    institution = next((line.institution for line in lines if line.institution), None)
    institution = institution or header.institution
    return ParsedBatch(
        parser="generic_llm",
        account=AccountHint(
            last4=last4,
            institution=institution,
            display_name=account_display_name(institution, last4),
            account_type=AccountType.SAVINGS,
        ),
        period_start=header.period_start,
        period_end=header.period_end,
        opening=header.opening,
        closing=header.closing,
        lines=lines,
    )


def _compact_complete() -> CompleteFn | None:
    router = LLMRouter()
    if router.provider_for("compact") is None:
        return None

    def call(messages: list[dict[str, str]]) -> dict[str, Any] | None:
        parsed = router.complete("compact", messages)
        return parsed if isinstance(parsed, dict) else None

    return call


def _lines(payload: Any) -> list[ParsedLine]:
    if not isinstance(payload, dict) or not isinstance(payload.get("lines"), list):
        return []
    parsed = [_line(item) for item in payload["lines"]]
    return [line for line in parsed if line is not None]


def _line(item: Any) -> ParsedLine | None:
    if not isinstance(item, dict):
        return None
    description = str(item.get("description") or "").strip()
    if not description or "posted_at" not in item or "amount" not in item:
        return None
    try:
        amount = parse_inr(item["amount"])
        when = posted_at(str(item["posted_at"]))
    except (InvalidOperation, ValueError, TypeError, IndexError, ArithmeticError):
        return None
    last4 = item.get("last4")
    last4_s = str(last4).strip() if last4 else ""
    if len(last4_s) > 4:
        last4_s = last4_s[-4:]
    institution = item.get("institution")
    return ParsedLine(
        posted_at=when,
        amount=amount,
        description=description,
        channel=infer_channel(description),
        last4=last4_s or None,
        institution=str(institution) if institution else None,
    )
