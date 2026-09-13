from decimal import Decimal

import pytest

from finsca.core.money import from_paise, parse_inr, to_paise


def test_parse_inr_quantizes_to_paise() -> None:
    assert parse_inr("10.1") == Decimal("10.10")
    assert parse_inr(10.1) == Decimal("10.10")


def test_to_paise_and_back_roundtrip() -> None:
    amount = parse_inr("18420.50")
    assert to_paise(amount) == 1842050
    assert from_paise(1842050) == amount


def test_negative_amounts_stay_signed() -> None:
    assert to_paise(parse_inr("-99.09")) == -9909
    assert from_paise(-9909) == Decimal("-99.09")


def test_invalid_money_raises() -> None:
    with pytest.raises(Exception):
        parse_inr("not-a-rupee")
