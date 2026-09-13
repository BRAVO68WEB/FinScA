"""Apply self-transfer pairs and learned review rules to the ledger."""

from __future__ import annotations

from sqlalchemy.orm import Session

from finsca.core.enums import Category, IncomeReview, Intent
from finsca.core.ids import new_id
from finsca.core.models import Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import rules as rule_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.finance.self_transfer import find_pairs


def link_self_transfers(session: Session, *, window_hours: int = 72) -> int:
    pairs = find_pairs(tx_repo.list_all(session), account_repo.list_all(session), window_hours=window_hours)
    for pair in pairs:
        tx_repo.mark_self_transfer(session, pair.debit_id, pair.credit_id, new_id())
    return len(pairs)


def apply_rules(session: Session) -> int:
    applied = 0
    for tx in tx_repo.list_pending_review(session):
        rule = rule_repo.match(session, tx)
        if rule is None or tx.id is None:
            continue
        intent = Intent(rule.intent) if rule.intent else Intent.TRANSFER
        category = Category(rule.category) if rule.category else None
        exclude = intent in {Intent.TRANSFER, Intent.SELF_TRANSFER}
        review = IncomeReview.TRANSFER if exclude else IncomeReview.INCOME
        tx_repo.apply_review(
            session,
            tx.id,
            intent=intent,
            income_review=review,
            exclude_from_cashflow=exclude,
            category=category,
        )
        applied += 1
    return applied


def pending_credits(session: Session) -> list[Transaction]:
    return tx_repo.list_pending_review(session)
