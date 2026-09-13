from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from finsca.core.enums import Channel, SourceKind
from finsca.ingest.alerts import alerts_to_batch, parse_alert
from finsca.ingest.sms.loaders import load_sms

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sms"


def test_parse_hdfc_debit_alert() -> None:
    hit = parse_alert("Rs.250.00 debited from a/c XX4521 on 01-08-26 to SWIGGY via UPI Ref 111")
    assert hit is not None
    assert hit.last4 == "4521"
    assert hit.amount == Decimal("-250.00")
    assert hit.posted_at.date().isoformat() == "2026-08-01"
    assert hit.channel == Channel.UPI
    assert "SWIGGY" in hit.description.upper()


def test_parse_hdfc_credit_alert() -> None:
    hit = parse_alert("Your A/c XX4521 is credited with Rs.12500.00 on 04-08-26 by NEFT SALARY")
    assert hit is not None
    assert hit.amount == Decimal("12500.00")
    assert hit.channel == Channel.NEFT


def test_parse_sms_xml_dump() -> None:
    batch = alerts_to_batch(load_sms(FIXTURES / "hdfc_alerts.xml"), SourceKind.SMS, "sms")
    assert batch.source_kind is SourceKind.SMS
    assert len(batch.lines) == 2
    assert {line.last4 for line in batch.lines} == {"4521"}
    assert sum(line.amount for line in batch.lines) == Decimal("12250.00")
