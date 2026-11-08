from __future__ import annotations

from finsca.finance.cc_bills import parse_bill_pay


def test_parse_icici_billpay() -> None:
    hint = parse_bill_pay("ICICI BIL/INFT/FFI0906993/CC BillPay-0003/Self")
    assert hint is not None
    assert hint.institution == "ICICI"
    assert hint.last4 == "0003"


def test_parse_cred_club_not_interest_credit() -> None:
    assert parse_bill_pay("UPI/P2M/609635402980/CRED Club /paymen/AXIS BANK") is not None
    assert parse_bill_pay("UPI/DR/644312932954/ CRED Clu/UTIB/cred.cl/") is not None
    assert parse_bill_pay("INTEREST CREDIT UPI/DR/Gullak") is None
    assert parse_bill_pay("VISA MERCH Refund WWW AMAZON IN") is None
