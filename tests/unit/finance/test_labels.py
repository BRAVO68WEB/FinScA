from __future__ import annotations

from finsca.config.taxonomy import MerchantHint
from finsca.core.enums import Category
from finsca.finance.labels import match_merchant
from finsca.llm.redaction import redact


def test_match_merchant_word_boundary() -> None:
    hints = (
        MerchantHint(match="SWIGGY", category=Category.DINING),
        MerchantHint(match="AMAZON", category=Category.SHOPPING),
    )
    assert match_merchant("ECOM PUR/SWIGGY PVT LT", hints) is Category.DINING
    assert match_merchant("VISA MERCH Refund WWW AMAZON IN", hints) is Category.SHOPPING
    assert match_merchant("RANDOM PAY", hints) is None


def test_redact_strips_long_digits_and_pan() -> None:
    text = redact("UPI/653124283200/ FPZPB7616J a/c 922010063724004")
    assert "653124283200" not in text
    assert "FPZPB7616J" not in text
    assert "XXXX" in text
