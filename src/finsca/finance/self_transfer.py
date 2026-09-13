"""Pair opposite legs of an own-account hop. Pure: no I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from finsca.core.models import Account, Transaction
from finsca.core.money import to_paise
from finsca.finance.normalize import normalize_description

_REF = re.compile(r"\d{10,}")


@dataclass(frozen=True)
class TransferPair:
    debit_id: str
    credit_id: str


def find_pairs(
    transactions: list[Transaction],
    accounts: list[Account],
    *,
    window_hours: int = 72,
) -> list[TransferPair]:
    own = {item.id: item for item in accounts if item.is_own and item.id}
    if len(own) < 2:
        return []
    unused = [
        tx
        for tx in transactions
        if tx.id
        and tx.account_id in own
        and tx.self_transfer_group_id is None
        and to_paise(tx.amount) != 0
    ]
    debits = [tx for tx in unused if tx.amount < 0]
    credits = [tx for tx in unused if tx.amount > 0]
    window = timedelta(hours=window_hours)
    used: set[str] = set()
    pairs: list[TransferPair] = []
    for debit in sorted(debits, key=lambda tx: tx.posted_at):
        if debit.id in used:
            continue
        match = _best_credit(debit, credits, own, window, used)
        if match is None or debit.id is None or match.id is None:
            continue
        used.add(debit.id)
        used.add(match.id)
        pairs.append(TransferPair(debit_id=debit.id, credit_id=match.id))
    return pairs


def _best_credit(
    debit: Transaction,
    credits: list[Transaction],
    accounts: dict[str, Account],
    window: timedelta,
    used: set[str],
) -> Transaction | None:
    debit_paise = abs(to_paise(debit.amount))
    in_window: list[tuple[int, Transaction]] = []
    for credit in credits:
        if credit.id in used or credit.account_id == debit.account_id:
            continue
        if abs(to_paise(credit.amount)) != debit_paise:
            continue
        delta = abs(credit.posted_at - debit.posted_at)
        if delta > window:
            continue
        in_window.append((int(delta.total_seconds()), credit))
    if not in_window:
        return None
    signaled = [item for item in in_window if _linked(debit, item[1], accounts)]
    if not signaled:
        return None
    signaled.sort(key=lambda item: item[0])
    return signaled[0][1]


def _linked(debit: Transaction, credit: Transaction, accounts: dict[str, Account]) -> bool:
    if _refs(debit) & _refs(credit):
        return True
    other_credit = accounts.get(credit.account_id)
    other_debit = accounts.get(debit.account_id)
    if other_credit and _mentions_account(debit, other_credit):
        return True
    if other_debit and _mentions_account(credit, other_debit):
        return True
    return False


def _refs(tx: Transaction) -> set[str]:
    return set(_REF.findall(tx.description_raw)) | set(_REF.findall(tx.description_norm))


def _mentions_account(tx: Transaction, account: Account) -> bool:
    blob = normalize_description(f"{tx.description_raw} {tx.description_norm}")
    tokens = [account.last4, *account.holder_aliases, *account.upi_vpas]
    for token in tokens:
        if token and re.search(rf"\b{re.escape(token.upper())}\b", blob):
            return True
    return False
