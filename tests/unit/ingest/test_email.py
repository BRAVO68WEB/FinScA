from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from finsca.core.enums import SourceKind
from finsca.ingest.alerts import alerts_to_batch
from finsca.ingest.email.mailbox import load_email

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "email"


def test_parse_eml_bank_alert() -> None:
    batch = alerts_to_batch(load_email(FIXTURES / "hdfc_debit.eml"), SourceKind.EMAIL, "email")
    assert batch.source_kind is SourceKind.EMAIL
    assert len(batch.lines) == 1
    assert batch.lines[0].last4 == "4521"
    assert batch.lines[0].amount == Decimal("-250.00")
