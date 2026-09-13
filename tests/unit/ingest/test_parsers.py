from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from finsca.core.enums import Channel
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.generic import parse_generic
from finsca.ingest.pdf.hdfc import parse_hdfc

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "statements"


def test_generic_parser_reads_period_balances_and_signs() -> None:
    text = (FIXTURES / "generic.txt").read_text()
    batch = parse_generic(text)
    assert batch.account.last4 == "4521"
    assert batch.opening == Decimal("10000.00")
    assert batch.closing == Decimal("22250.00")
    assert batch.period_start.isoformat() == "2026-08-01"
    assert batch.period_end.isoformat() == "2026-08-31"
    assert len(batch.lines) == 2
    assert batch.lines[0].amount == Decimal("-250.00")
    assert batch.lines[0].channel == Channel.UPI
    assert batch.lines[1].amount == Decimal("12500.00")
    assert batch.lines[1].channel == Channel.NEFT


def test_hdfc_parser_uses_withdrawal_deposit_columns() -> None:
    text = (FIXTURES / "hdfc.txt").read_text()
    batch = parse_hdfc(text)
    assert batch.parser == "hdfc"
    assert batch.account.institution == "HDFC"
    assert batch.account.last4 == "4521"
    assert len(batch.lines) == 2
    assert batch.lines[0].amount == Decimal("-250.00")
    assert batch.lines[1].amount == Decimal("12500.00")
    assert batch.opening == Decimal("10000.00")
    assert batch.closing == Decimal("22250.00")


def test_dispatch_picks_hdfc() -> None:
    text = (FIXTURES / "hdfc.txt").read_text()
    batch = parse_statement(text, "hdfc")
    assert batch.parser == "hdfc"
    assert len(batch.lines) == 2


def test_axis_parser_uses_running_balance() -> None:
    text = (FIXTURES / "axis.txt").read_text()
    batch = parse_statement(text, "axis")
    assert batch.parser == "axis"
    assert batch.account.last4 == "4004"
    assert len(batch.lines) == 2
    assert batch.lines[0].amount == Decimal("60000.00")
    assert batch.lines[1].amount == Decimal("-100.00")
    assert batch.opening + sum(line.amount for line in batch.lines) == batch.closing


def test_icici_parser_signs_from_balance() -> None:
    text = (FIXTURES / "icici.txt").read_text()
    batch = parse_statement(text, "icici")
    assert batch.parser == "icici"
    assert batch.account.last4 == "0044"
    assert len(batch.lines) == 4
    assert batch.lines[0].amount == Decimal("47.00")
    assert batch.lines[2].amount == Decimal("56900.00")
    assert batch.opening + sum(line.amount for line in batch.lines) == batch.closing


def test_idfc_parser_reads_dr_cr_and_summary() -> None:
    text = (FIXTURES / "idfc.txt").read_text()
    batch = parse_statement(text, "idfc")
    assert batch.parser == "idfc"
    assert batch.account.last4 == "9033"
    assert len(batch.lines) == 2
    assert batch.lines[0].amount == Decimal("-10000.00")
    assert batch.lines[1].amount == Decimal("5.00")
    assert batch.opening == Decimal("94617.32")
    assert batch.closing == Decimal("84622.32")
