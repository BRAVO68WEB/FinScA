"""Apply category labels: user rules, YAML merchants, then optional compact model."""

from __future__ import annotations

from finsca.config.settings import Settings
from finsca.config.taxonomy import Taxonomy, load_taxonomy
from finsca.core.enums import Category, Intent, LabelSource
from finsca.core.models import Transaction
from finsca.db.repositories import rules as rule_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.finance.labels import match_merchant
from finsca.ledger.apply import resolve_transaction
from finsca.llm.compact import suggest_labels
from sqlalchemy.orm import Session

_INCOME = {Category.SALARY, Category.FREELANCE, Category.BUSINESS_INCOME, Category.INTEREST}
_TRANSFER = {Category.TRANSFER, Category.SELF_TRANSFER}


def intent_for(category: Category) -> Intent:
    if category in _INCOME:
        return Intent.INCOME
    if category in _TRANSFER:
        return Intent.TRANSFER
    if category is Category.EMI:
        return Intent.EMI
    if category is Category.INVESTMENT:
        return Intent.INVESTMENT
    if category is Category.REFUND:
        return Intent.REFUND
    return Intent.EXPENSE


def apply_labels(session: Session, settings: Settings | None = None, *, complete=None) -> dict[str, int]:
    cfg = settings or Settings()
    taxonomy = load_taxonomy()
    counts = {"rules": 0, "yaml": 0, "compact": 0}
    unlabeled = tx_repo.list_unlabeled(session)
    still: list[Transaction] = []
    for tx in unlabeled:
        if tx.id is None:
            continue
        rule = rule_repo.match(session, tx)
        if rule and rule.category:
            _write(session, tx.id, rule.category, LabelSource.RULE)
            counts["rules"] += 1
            continue
        still.append(tx)
    leftover: list[Transaction] = []
    for tx in still:
        if tx.id is None:
            continue
        category = match_merchant(tx.description_raw, taxonomy.merchants)
        if category:
            _write(session, tx.id, category, LabelSource.RULE)
            counts["yaml"] += 1
            continue
        leftover.append(tx)
    if leftover and complete is not None:
        counts["compact"] = _apply_compact(session, leftover, taxonomy, cfg, complete)
    elif leftover and not cfg.llm_off:
        from finsca.llm.router import compact_available, complete_compact

        if compact_available(cfg):
            counts["compact"] = _apply_compact(
                session, leftover, taxonomy, cfg, lambda messages: complete_compact(messages, cfg)
            )
    return counts


def label_one(
    session: Session,
    token: str,
    category: Category,
    *,
    remember: str | None = None,
) -> Transaction:
    tx = resolve_transaction(session, token)
    if tx is None or tx.id is None:
        raise KeyError(token)
    updated = _write(session, tx.id, category, LabelSource.MANUAL)
    if remember:
        rule_repo.add(
            session,
            match_field="description_contains",
            match_value=remember,
            intent=intent_for(category),
            category=category,
        )
    return updated


def _apply_compact(session: Session, rows: list[Transaction], taxonomy: Taxonomy, settings: Settings, complete) -> int:
    applied = 0
    batch = rows[:25]
    guesses = suggest_labels(
        [tx.description_raw for tx in batch],
        taxonomy.categories,
        complete=complete,
        min_confidence=settings.label_min_confidence,
    )
    by_index = {item.index: item for item in guesses}
    for index, tx in enumerate(batch):
        guess = by_index.get(index)
        if guess is None or tx.id is None:
            continue
        _write(session, tx.id, guess.category, LabelSource.MODEL, confidence=guess.confidence)
        applied += 1
    return applied


def _write(
    session: Session,
    tx_id: str,
    category: Category,
    source: LabelSource,
    confidence: float | None = None,
) -> Transaction:
    return tx_repo.set_label(
        session,
        tx_id,
        category,
        source=source,
        confidence=confidence,
        intent=intent_for(category),
    )
