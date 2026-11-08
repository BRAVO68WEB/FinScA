"""Mark bank-side credit-card bill pays as self-transfers onto CC accounts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from finsca.core.enums import AccountType, Category, IncomeReview, Intent
from finsca.core.ids import new_id
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.finance.cc_bills import BillHint, parse_bill_pay


def inject_cc_bills(session: Session) -> int:
    marked = 0
    for tx in tx_repo.list_all(session):
        if tx.self_transfer_group_id or tx.intent is Intent.SELF_TRANSFER:
            continue
        if tx.amount >= 0:
            continue
        hint = parse_bill_pay(tx.description_raw)
        if hint is None or tx.id is None:
            continue
        card = _card_account(session, hint)
        if card.id is None:
            continue
        if not tx_repo.mark_self_transfer(session, tx.id, tx.id, new_id()):
            continue
        tx_repo.apply_review(
            session,
            tx.id,
            intent=Intent.SELF_TRANSFER,
            income_review=IncomeReview.SKIPPED,
            exclude_from_cashflow=True,
            category=Category.TRANSFER,
        )
        marked += 1
    return marked


def _card_account(session: Session, hint: BillHint) -> Account:
    for account in account_repo.list_all(session):
        if account.type is not AccountType.CREDIT_CARD:
            continue
        if (account.institution or "").casefold() != hint.institution.casefold():
            continue
        if hint.last4 and account.last4 != hint.last4:
            continue
        return account
    return account_repo.add(
        session,
        Account(
            display_name=hint.display_name,
            type=AccountType.CREDIT_CARD,
            institution=hint.institution,
            last4=hint.last4,
        ),
    )
