"""LLM leftovers stay quiet without a provider and parse when a fake complete is injected."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from finsca.core.enums import SourceKind
from finsca.ingest.alerts import AlertRecord, alerts_to_batch
from finsca.ingest.pdf.base import parse_statement

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "statements"


def test_known_statement_does_not_call_the_model() -> None:
    def boom(_messages: list[dict[str, str]]) -> dict[str, object]:
        raise AssertionError("known statement called the model")

    batch = parse_statement((FIXTURES / "hdfc.txt").read_text(), "hdfc", complete=boom)
    assert batch.parser == "hdfc"
    assert len(batch.lines) == 2


def test_unknown_statement_uses_the_injected_complete() -> None:
    def fake(messages: list[dict[str, str]]) -> dict[str, object]:
        body = messages[-1]["content"]
        assert "123456789012" not in body
        assert "XXXX" in body
        return {
            "lines": [
                {
                    "posted_at": "2026-08-01",
                    "amount": "-10.00",
                    "description": "SHOP",
                    "last4": "9999",
                }
            ]
        }

    text = "Mystery Bank Statement\nAccount 123456789012\nno dated rows\n"
    batch = parse_statement(text, None, complete=fake)
    assert batch.parser == "generic_llm"
    assert batch.account.last4 == "9999"
    assert batch.lines[0].amount == Decimal("-10.00")
    assert batch.lines[0].description == "SHOP"


def test_router_off_invents_no_statement_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSCA_LLM_OFF", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    batch = parse_statement("Mystery Bank Statement\nno rows\n", None)
    assert batch.lines == []


def test_template_hit_does_not_call_the_model() -> None:
    def boom(_messages: list[dict[str, str]]) -> dict[str, object]:
        raise AssertionError("template hit called the model")

    batch = alerts_to_batch(
        [AlertRecord("Rs.250.00 debited from a/c XX4521 on 01-08-26 to SWIGGY via UPI Ref 111")],
        SourceKind.SMS,
        "sms",
        complete=boom,
    )
    assert len(batch.lines) == 1
    assert batch.lines[0].amount == Decimal("-250.00")


def test_template_miss_uses_the_injected_complete() -> None:
    def fake(messages: list[dict[str, str]]) -> dict[str, object]:
        body = messages[-1]["content"]
        assert "9999999999" not in body
        assert "XXXXXXXXXX" in body
        return {
            "posted_at": "2026-08-02",
            "amount": "-20.00",
            "description": "CAFE",
            "last4": "1111",
            "institution": "HDFC",
        }

    batch = alerts_to_batch(
        [AlertRecord("paid 9999999999 at cafe")],
        SourceKind.SMS,
        "sms",
        complete=fake,
    )
    assert len(batch.lines) == 1
    assert batch.lines[0].amount == Decimal("-20.00")
    assert batch.lines[0].last4 == "1111"
    assert batch.warnings == []
