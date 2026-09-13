from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.clock import utcnow
from finsca.core.enums import Category, Intent
from finsca.core.ids import new_id
from finsca.core.models import Transaction
from finsca.db import schema as tables
from finsca.finance.normalize import normalize_description


@dataclass(frozen=True)
class MatchedRule:
    intent: Intent
    category: Category | None
    match_value: str


def add(
    session: Session,
    *,
    match_field: str,
    match_value: str,
    intent: Intent,
    category: Category | None = None,
) -> MatchedRule:
    value = normalize_description(match_value)
    row = tables.Rule(
        id=new_id(),
        match_field=match_field,
        match_value=value,
        intent=intent.value,
        category=category.value if category else None,
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return MatchedRule(intent=intent, category=category, match_value=value)


def match(session: Session, tx: Transaction) -> MatchedRule | None:
    blob = normalize_description(f"{tx.description_raw} {tx.counterparty or ''}")
    for row in session.scalars(select(tables.Rule)):
        needle = (row.match_value or "").strip()
        if not needle or not row.intent:
            continue
        hit = False
        if row.match_field == "description_contains" and needle in blob:
            hit = True
        if (
            row.match_field == "counterparty"
            and tx.counterparty
            and needle in normalize_description(tx.counterparty)
        ):
            hit = True
        if hit:
            category = Category(row.category) if row.category else None
            return MatchedRule(intent=Intent(row.intent), category=category, match_value=needle)
    return None
