from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.clock import utcnow
from finsca.core.enums import Category, Intent
from finsca.core.ids import new_id
from finsca.core.models import Transaction
from finsca.db import schema as tables
from finsca.finance.normalize import normalize_description


def add(
    session: Session,
    *,
    match_field: str,
    match_value: str,
    intent: Intent,
    category: Category | None = None,
) -> tables.Rule:
    row = tables.Rule(
        id=new_id(),
        match_field=match_field,
        match_value=normalize_description(match_value),
        intent=intent.value,
        category=category.value if category else None,
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def list_all(session: Session) -> list[tables.Rule]:
    return list(session.scalars(select(tables.Rule)))


def match(session: Session, tx: Transaction) -> tables.Rule | None:
    blob = normalize_description(f"{tx.description_raw} {tx.counterparty or ''}")
    for rule in list_all(session):
        needle = (rule.match_value or "").strip()
        if not needle:
            continue
        if rule.match_field == "description_contains" and needle in blob:
            return rule
        if rule.match_field == "counterparty" and tx.counterparty and needle in normalize_description(tx.counterparty):
            return rule
    return None
