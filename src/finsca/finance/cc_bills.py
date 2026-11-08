"""Detect credit-card bill payments from bank narrations. Pure."""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsca.finance.normalize import normalize_description

_BILLPAY = re.compile(r"CC\s*BILL\s*PAY[- ]?(?P<last4>\d{4})?", re.I)
_CRED_CLUB = re.compile(r"\bCRED\s*CLU", re.I)
_CRED_WALLET = re.compile(r"\bCRED\s*WALLET\b", re.I)
_CRED_PAY = re.compile(r"\bCRED\b.*/paymen", re.I)


@dataclass(frozen=True)
class BillHint:
    institution: str
    last4: str | None
    display_name: str


def parse_bill_pay(description: str) -> BillHint | None:
    blob = normalize_description(description)
    bill = _BILLPAY.search(blob)
    if bill:
        last4 = bill.group("last4")
        return BillHint(institution="ICICI", last4=last4, display_name=f"ICICI CC {last4 or ''}".strip())
    if _CRED_WALLET.search(blob):
        return BillHint(institution="CRED", last4=None, display_name="CRED Wallet")
    if _CRED_CLUB.search(blob) or _CRED_PAY.search(blob):
        return BillHint(institution="CRED", last4=None, display_name="CRED Cards")
    return None
