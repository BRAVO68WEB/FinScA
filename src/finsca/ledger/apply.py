"""Apply self-transfer pairs and review decisions to the ledger."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy.orm import Session

from finsca.core.enums import Category, IncomeReview, Intent
from finsca.core.ids import new_id
from finsca.core.models import Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import rules as rule_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.finance.self_transfer import find_pairs


class ReviewDecision(StrEnum):
    INCOME = "income"
    TRANSFER = "transfer"
    SKIP = "skip"


def link_self_transfers(session: Session, *, window_hours: int = 72) -> int:
    pairs = find_pairs(tx_repo.list_all(session), account_repo.list_all(session), window_hours=window_hours)
    linked = 0
    for pair in pairs:
        if tx_repo.mark_self_transfer(session, pair.debit_id, pair.credit_id, new_id()):
            linked += 1
    return linked


def apply_rules(session: Session) -> int:
    applied = 0
    for tx in tx_repo.list_pending_review(session):
        rule = rule_repo.match(session, tx)
        if rule is None or tx.id is None:
            continue
        review(
            session,
            tx.id,
            ReviewDecision.TRANSFER if rule.intent in {Intent.TRANSFER, Intent.SELF_TRANSFER} else ReviewDecision.INCOME,
            category=rule.category,
        )
        applied += 1
    return applied


def review(
    session: Session,
    tx_id: str,
    decision: ReviewDecision,
    *,
    category: Category | None = None,
    remember: str | None = None,
) -> Transaction:
    current = tx_repo.get(session, tx_id)
    if current is None:
        raise KeyError(tx_id)
    if decision is ReviewDecision.INCOME:
        updated = tx_repo.apply_review(
            session,
            tx_id,
            intent=Intent.INCOME,
            income_review=IncomeReview.INCOME,
            exclude_from_cashflow=False,
            category=category or Category.OTHER,
        )
    elif decision is ReviewDecision.TRANSFER:
        updated = tx_repo.apply_review(
            session,
            tx_id,
            intent=Intent.TRANSFER,
            income_review=IncomeReview.TRANSFER,
            exclude_from_cashflow=True,
        )
    else:
        updated = tx_repo.apply_review(
            session,
            tx_id,
            intent=current.intent,
            income_review=IncomeReview.SKIPPED,
            exclude_from_cashflow=current.exclude_from_cashflow,
        )
    if remember and decision is not ReviewDecision.SKIP:
        rule_repo.add(
            session,
            match_field="description_contains",
            match_value=remember,
            intent=Intent.INCOME if decision is ReviewDecision.INCOME else Intent.TRANSFER,
            category=category,
        )
    return updated


def resolve_transaction(session: Session, token: str) -> Transaction | None:
    needle = token.strip()
    pending = tx_repo.list_pending_review(session)
    hits = [tx for tx in pending if tx.id and tx.id.startswith(needle)]
    if len(hits) == 1:
        return hits[0]
    hits = [tx for tx in tx_repo.list_all(session) if tx.id and tx.id.startswith(needle)]
    if len(hits) == 1:
        return hits[0]
    return None
