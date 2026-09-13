"""Infer payment channel from a narration."""

from finsca.core.enums import Channel

_MARKERS: tuple[tuple[str, Channel], ...] = (
    ("UPI", Channel.UPI),
    ("NEFT", Channel.NEFT),
    ("IMPS", Channel.IMPS),
    ("RTGS", Channel.RTGS),
    ("NACH", Channel.NACH),
    ("ACH", Channel.NACH),
    ("ATM", Channel.ATM),
    ("POS", Channel.DEBIT_CARD),
    ("DEBIT CARD", Channel.DEBIT_CARD),
    ("CREDIT CARD", Channel.CREDIT_CARD),
    ("CHQ", Channel.CHEQUE),
    ("CHEQUE", Channel.CHEQUE),
    ("CASH", Channel.CASH),
)


def infer_channel(description: str) -> Channel:
    upper = description.upper()
    for marker, channel in _MARKERS:
        if marker in upper:
            return channel
    return Channel.OTHER
