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
    own = [item for item in accounts if item.is_own and item.id]
    if len(own) < 2:
        return []
    by_id = {item.id: item for item in own if item.id}
    unused = [
        tx
        for tx in transactions
        if tx.id
        and tx.account_id in by_id
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
        match = _best_credit(debit, credits, by_id, window, used)
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
    candidates: list[tuple[int, int, Transaction]] = []
    for credit in credits:
        if credit.id in used or credit.account_id == debit.account_id:
            continue
        if abs(to_paise(credit.amount)) != debit_paise:
            continue
        delta = abs(credit.posted_at - debit.posted_at)
        if delta > window:
            continue
        score = _score(debit, credit, accounts)
        candidates.append((score, int(delta.total_seconds()), credit))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    best_score, _, best = candidates[0]
    tied = [item for item in candidates if item[0] == best_score and item[2].id != best.id]
    if best_score == 0 and tied:
        return None
    if best_score == 0 and len(candidates) > 1:
        return None
    return best


def _score(debit: Transaction, credit: Transaction, accounts: dict[str, Account]) -> int:
    score = 0
    if _shared_refs(debit, credit):
        score += 4
    other_from_debit = accounts.get(credit.account_id)
    other_from_credit = accounts.get(debit.account_id)
    if other_from_debit and _mentions(debit, other_from_debit):
        score += 2
    if other_from_credit and _mentions(credit, other_from_credit):
        score += 2
    if _bill_pay(debit) or _bill_pay(credit):
        score += 1
    return score


def _shared_refs(left: Transaction, right: Transaction) -> bool:
    return bool(_refs(left) & _refs(right))


def _refs(tx: Transaction) -> set[str]:
    return set(_REF.findall(tx.description_raw)) | set(_REF.findall(tx.description_norm))


def _mentions(tx: Transaction, account: Account) -> bool:
    blob = normalize_description(f"{tx.description_raw} {tx.description_norm}")
    tokens = {account.last4 or "", *(alias.upper() for alias in account.holder_aliases)}
    tokens.discard("")
    if account.institution:
        tokens.update(_institution_tokens(account.institution))
    return any(token in blob for token in tokens)


def _institution_tokens(institution: str) -> set[str]:
    key = institution.upper()
    extra = {
        "AXIS": {"AXIS", "UTIB"},
        "ICICI": {"ICICI", "ICIC"},
        "IDFC": {"IDFC", "IDFB"},
        "HDFC": {"HDFC"},
        "SBI": {"SBI", "SBIN"},
    }
    return extra.get(key, {key})


def _bill_pay(tx: Transaction) -> bool:
    blob = normalize_description(tx.description_raw)
    return any(token in blob for token in ("BILLPAY", "BILL PAY", "CC BILL", "CRED CLUB", "CRED WALLET"))
