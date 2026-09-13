from decimal import Decimal, ROUND_HALF_EVEN

PAISE = Decimal("0.01")


def parse_inr(value: object) -> Decimal:
    return Decimal(str(value)).quantize(PAISE, rounding=ROUND_HALF_EVEN)


def to_paise(amount: Decimal) -> int:
    return int((parse_inr(amount) * 100).to_integral_value(rounding=ROUND_HALF_EVEN))


def from_paise(paise: int) -> Decimal:
    return (Decimal(paise) / Decimal(100)).quantize(PAISE)
