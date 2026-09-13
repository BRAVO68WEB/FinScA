from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.orm import Session

from finsca.core.enums import IncomeReview, Intent, MonthSource
from finsca.core.models import Account, AccountMonth, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.repositories.transactions import DuplicateTransactionError
from finsca.ingest.errors import ParseError
from finsca.ingest.pdf.header import account_display_name
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine


@dataclass(frozen=True)
class PersistResult:
    account: Account | None
    inserted: int
    dupes: int
    pending_review: int


def persist_batch(session: Session, batch: ParsedBatch, run_id: str) -> PersistResult:
    groups = _group_lines(batch)
    if not groups:
        raise ParseError("statement has no account last4")
    inserted = dupes = pending = 0
    last_account: Account | None = None
    for hint, lines in groups:
        account = find_or_create_account(session, hint)
        if account.id is None:
            raise RuntimeError("persisted account missing id")
        last_account = account
        if hint.last4 == batch.account.last4:
            _write_month(session, account.id, batch)
        for line in lines:
            created, is_new = _add_or_merge(session, account.id, line, batch, run_id)
            if is_new:
                inserted += 1
                if created.amount > 0:
                    pending += 1
            else:
                dupes += 1
    return PersistResult(account=last_account, inserted=inserted, dupes=dupes, pending_review=pending)


def _add_or_merge(
    session: Session,
    account_id: str,
    line: ParsedLine,
    batch: ParsedBatch,
    run_id: str,
) -> tuple[Transaction, bool]:
    credit = line.amount > 0
    payload = Transaction(
        account_id=account_id,
        posted_at=line.posted_at,
        amount=line.amount,
        description_raw=line.description,
        channel=line.channel,
        source_kind=batch.source_kind,
        ingest_run_id=run_id,
        intent=Intent.UNKNOWN,
        income_review=IncomeReview.PENDING if credit else IncomeReview.SKIPPED,
    )
    existing = tx_repo.find_same_event(session, account_id, payload.posted_at, payload.amount)
    if existing is not None:
        tx_repo.enrich_source(session, existing, batch.source_kind)
        return existing, False
    try:
        return tx_repo.add(session, payload), True
    except DuplicateTransactionError as exc:
        tx_repo.enrich_source(session, exc.existing, batch.source_kind)
        return exc.existing, False


def _group_lines(batch: ParsedBatch) -> list[tuple[AccountHint, list[ParsedLine]]]:
    buckets: dict[tuple[str, str | None], list[ParsedLine]] = defaultdict(list)
    for line in batch.lines:
        last4 = line.last4 or batch.account.last4
        if not last4:
            continue
        institution = line.institution or batch.account.institution
        buckets[(last4, institution)].append(line)
    groups: list[tuple[AccountHint, list[ParsedLine]]] = []
    for (last4, institution), lines in buckets.items():
        display = batch.account.display_name if last4 == batch.account.last4 else None
        groups.append(
            (
                AccountHint(
                    last4=last4,
                    institution=institution,
                    display_name=display or account_display_name(institution, last4),
                    account_type=batch.account.account_type,
                ),
                lines,
            )
        )
    return groups


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
