from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from finsca.core.enums import SourceKind
from finsca.ingest.email.parsers import parse_email_file

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "email"


def test_parse_eml_bank_alert() -> None:
    batch = parse_email_file(FIXTURES / "hdfc_debit.eml")
    assert batch.source_kind is SourceKind.EMAIL
    assert len(batch.lines) == 1
    assert batch.lines[0].last4 == "4521"
    assert batch.lines[0].amount == Decimal("-250.00")
