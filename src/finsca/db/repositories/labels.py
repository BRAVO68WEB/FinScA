"""Category lookup: a stored rule, then the YAML merchant map."""

from __future__ import annotations

from sqlalchemy.orm import Session

from finsca.config.taxonomy import Taxonomy, load_taxonomy
from finsca.core.enums import Category, LabelSource
from finsca.core.models import Transaction
from finsca.db.repositories import rules as rule_repo
from finsca.finance.labels import match_merchant


def lookup(
    session: Session,
    tx: Transaction,
    taxonomy: Taxonomy | None = None,
) -> tuple[Category, LabelSource] | None:
    rule = rule_repo.match(session, tx)
    if rule and rule.category:
        return rule.category, LabelSource.RULE
    tax = taxonomy or load_taxonomy()
    hit = match_merchant(tx.description_raw, tax.merchants)
    if hit:
        return hit, LabelSource.TAXONOMY
    return None
