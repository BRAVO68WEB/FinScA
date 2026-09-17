from __future__ import annotations

from decimal import Decimal

from finsca.core.enums import AccountType
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.cards import parse_card


HDFC_CC = """
Tata Neu Plus HDFC Bank Credit Card Statement
Credit Card No. 402219XXXXXX3628
Billing Period 02 Jul, 2026 - 01 Aug, 2026
DATE & TIME TRANSACTION DESCRIPTION AMOUNT
03/07/2026| 18:42 EMI RELIANCE DIGITALHYDERABAD + 371 C 37,088.48 l
07/07/2026| 00:00 OFFUS EMI,PROCNG FEE C 299.00 l
"""

YES_CC = """
Credit Card Statement
YES BANK POP CLUB
Statement for YES BANK Card Number 3561XXXXXXXX5005
Statement Period: 17/07/2026 To 16/08/2026
17/07/2026 UPI_BLINKIT IND - Ref No: RT1 Miscellaneous Stores 1,354.00 Dr
18/07/2026 PAYMENT RECEIVED BBPS - Ref No: 99 31,279.76 Cr
"""

SBI_CC = """
GSTIN of SBI Card : 06AAECS5981K1ZV
Credit Card Number
XXXX XXXX XXXX XX44
Date Transaction Details Amount
05 Aug 26 PAYMENT RECEIVED 000DP0162 29,390.00 C
27 Aug 26 Amazon Seller Services Bangalore IN 615.00 D
"""

AXIS_SAVINGS = """
AXIS BANK LTD
Opening Balance 62,642.38
03-08-2026 UPI/P2M/658129627735/CRED 600.00
03-08-2026 VISA MERCH Refund /01-AUG-26/WWW 2,697.00
13-08-2026 NEFT/IDFB6225M0395252/Salary 200,000.00
Closing Balance 161,806.71
"""


def test_hdfc_card_rows_and_last4() -> None:
    batch = parse_card(HDFC_CC, bank_id="hdfc")
    assert batch.account.account_type is AccountType.CREDIT_CARD
    assert batch.account.last4 == "3628"
    assert len(batch.lines) == 2
    assert batch.lines[0].amount == Decimal("-37088.48")


def test_yes_card_dr_cr() -> None:
    batch = parse_card(YES_CC, bank_id="yes")
    assert batch.account.last4 == "5005"
    assert [line.amount for line in batch.lines] == [Decimal("-1354.00"), Decimal("31279.76")]


def test_sbi_card_c_d_and_filename_last4() -> None:
    batch = parse_card(
        SBI_CC,
        bank_id="sbi",
        filename="1a0721d7acb7_PRIME.card_sbicard.com_8819776404745323_04092026.pdf",
    )
    assert batch.account.last4 == "5323"
    assert batch.lines[0].amount == Decimal("29390.00")
    assert batch.lines[1].amount == Decimal("-615.00")


def test_axis_single_amount_lines_sign_from_narration() -> None:
    batch = parse_statement(AXIS_SAVINGS, "axis")
    assert len(batch.lines) == 3
    assert batch.lines[0].amount == Decimal("-600.00")
    assert batch.lines[1].amount == Decimal("2697.00")
    assert batch.lines[2].amount == Decimal("200000.00")
