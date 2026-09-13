"""Infer payment channel from a narration, and expense channel mix."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from finsca.core.enums import Channel
from finsca.core.models import Transaction

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


_MIX = (Channel.UPI, Channel.DEBIT_CARD, Channel.CREDIT_CARD)


def channel_mix(transactions: list[Transaction]) -> list[tuple[Channel, Decimal]]:
    from finsca.finance.habits import expense_txs

    totals: Counter[Channel] = Counter()
    for tx in expense_txs(transactions):
        if tx.channel in _MIX:
            totals[tx.channel] += abs(tx.amount)
    return [(channel, totals[channel]) for channel in _MIX]
