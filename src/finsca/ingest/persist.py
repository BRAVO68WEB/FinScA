from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from finsca.core.enums import IncomeReview, Intent, MonthSource, SourceKind
from finsca.core.models import Account, AccountMonth, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.repositories.transactions import DuplicateTransactionError
from finsca.ingest.errors import ParseError
from finsca.ingest.pdf.header import account_display_name
from finsca.ingest.types import AccountHint, ParsedBatch


@dataclass(frozen=True)
class PersistResult:
    account: Account
    inserted: int
    dupes: int
    pending_review: int


def persist_batch(session: Session, batch: ParsedBatch, run_id: str) -> PersistResult:
    account = find_or_create_account(session, batch.account)
    if account.id is None:
        raise RuntimeError("persisted account missing id")
    _write_month(session, account.id, batch)
    inserted = dupes = pending = 0
    for line in batch.lines:
        credit = line.amount > 0
        payload = Transaction(
            account_id=account.id,
            posted_at=line.posted_at,
            amount=line.amount,
            description_raw=line.description,
            channel=line.channel,
            source_kind=SourceKind.PDF,
            ingest_run_id=run_id,
            intent=Intent.UNKNOWN,
            income_review=IncomeReview.PENDING if credit else IncomeReview.SKIPPED,
        )
        try:
            tx_repo.add(session, payload)
            inserted += 1
            if credit:
                pending += 1
        except DuplicateTransactionError:
            dupes += 1
    return PersistResult(account=account, inserted=inserted, dupes=dupes, pending_review=pending)


def find_or_create_account(session: Session, hint: AccountHint) -> Account:
    if not hint.last4:
        raise ParseError("statement has no account last4")
    matches = account_repo.list_by_last4(session, hint.last4)
    if hint.institution:
        inst = [
            item
            for item in matches
            if (item.institution or "").casefold() == hint.institution.casefold()
        ]
        if len(inst) == 1:
            return inst[0]
        if len(inst) > 1:
            raise ParseError(f"ambiguous account {hint.last4} at {hint.institution}")
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ParseError(f"ambiguous account last4 {hint.last4}")
    return account_repo.add(
        session,
        Account(
            display_name=hint.display_name or account_display_name(hint.institution, hint.last4) or "Account",
            type=hint.account_type,
            institution=hint.institution,
            last4=hint.last4,
        ),
    )


def _write_month(session: Session, account_id: str, batch: ParsedBatch) -> None:
    if batch.opening is None or batch.closing is None:
        return
    period = batch.period_end or batch.period_start
    if period is None:
        return
    account_repo.set_month(
        session,
        AccountMonth(
            account_id=account_id,
            year=period.year,
            month=period.month,
            opening=batch.opening,
            closing=batch.closing,
            source=MonthSource.STATEMENT,
        ),
    )
