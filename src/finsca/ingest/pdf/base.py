from __future__ import annotations

import re
from typing import Any

from finsca.core.enums import AccountType
from finsca.ingest.detect import looks_like_statement
from finsca.ingest.pdf.axis import parse_axis
from finsca.ingest.pdf.cards import parse_card
from finsca.ingest.pdf.generic import parse_generic
from finsca.ingest.pdf.generic_llm import parse_unknown_statement
from finsca.ingest.pdf.hdfc import parse_hdfc
from finsca.ingest.pdf.icici import parse_icici
from finsca.ingest.pdf.idfc import parse_idfc
from finsca.ingest.pdf.sbi import parse_sbi
from finsca.ingest.types import ParsedBatch

_PARSERS = {
    "hdfc": parse_hdfc,
    "axis": parse_axis,
    "icici": parse_icici,
    "idfc": parse_idfc,
    "sbi": parse_sbi,
}
_CARDISH = re.compile(
    r"credit card|card statement|card number|my zone card|sbi card|tata neu plus",
    re.I,
)


def parse_statement(
    text: str,
    bank_id: str | None,
    *,
    filename: str = "",
    complete: Any = None,
) -> ParsedBatch:
    if _looks_like_card(text, filename):
        card = parse_card(text, bank_id=bank_id, filename=filename)
        if card.lines:
            return card
    if bank_id and bank_id in _PARSERS:
        batch = _PARSERS[bank_id](text)
    else:
        institution = bank_id.upper() if bank_id else None
        batch = parse_generic(text, parser=bank_id or "generic", institution=institution)
    if batch.lines and _looks_like_card(text, filename):
        batch.account.account_type = AccountType.CREDIT_CARD
    if batch.lines or not looks_like_statement(text, filename):
        return batch
    fallback = parse_unknown_statement(text, filename=filename, complete=complete)
    if fallback is not None and fallback.lines:
        if _looks_like_card(text, filename):
            fallback.account.account_type = AccountType.CREDIT_CARD
        return fallback
    return batch


def _looks_like_card(text: str, filename: str) -> bool:
    blob = f"{filename}\n{text[:2500]}"
    if re.search(r"savings account|consolidated statement|statement of transactions in savings", blob, re.I):
        return False
    return bool(_CARDISH.search(blob))
