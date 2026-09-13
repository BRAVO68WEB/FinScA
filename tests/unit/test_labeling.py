from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from finsca.cli.app import app
from finsca.config.settings import Settings
from finsca.core.enums import AccountType, Category, Channel, Intent, LabelSource, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ledger.labeling import apply_labels

runner = CliRunner()


def _tx(session: Session, desc: str, amount: str = "-119.00") -> Transaction:
    account = account_repo.list_all(session)
    if not account:
        created = account_repo.add(
            session,
            Account(display_name="AXIS 4004", type=AccountType.SAVINGS, institution="AXIS", last4="4004"),
        )
        account_id = created.id or ""
    else:
        account_id = account[0].id or ""
    row, _ = tx_repo.add_event(
        session,
        Transaction(
            account_id=account_id,
            posted_at=datetime(2026, 3, 14, tzinfo=timezone.utc),
            amount=Decimal(amount),
            description_raw=desc,
            source_kind=SourceKind.PDF,
            channel=Channel.UPI,
        ),
    )
    return row


def test_yaml_labels_swiggy(db_session: Session) -> None:
    tx = _tx(db_session, "ECOM PUR/SWIGGY PVT LT/8050899940")
    counts = apply_labels(db_session, Settings(llm_off=True))
    assert counts["yaml"] == 1
    labeled = tx_repo.get(db_session, tx.id or "")
    assert labeled is not None
    assert labeled.category is Category.DINING
    assert labeled.intent is Intent.EXPENSE
    assert labeled.label_source is LabelSource.TAXONOMY


def test_label_set_remember_applies_to_next(data_dir: Path, db_session: Session) -> None:
    first = _tx(db_session, "UPI/NAVIKARANA CONSUMER G/Paymen")
    second = _tx(db_session, "UPI/NAVIKARANA CONSUMER G/again", amount="-30.00")
    db_session.commit()
    result = runner.invoke(
        app,
        ["label", "set", (first.id or "")[:8], "shopping", "--remember", "--match", "NAVIKARANA"],
    )
    assert result.exit_code == 0, result.output
    auto = runner.invoke(app, ["label", "auto"])
    assert auto.exit_code == 0, auto.output
    leftover = runner.invoke(app, ["label"])
    assert leftover.exit_code == 0, leftover.output
    assert "no unlabeled" in leftover.output
    labeled = tx_repo.get(db_session, second.id or "")
    assert labeled is not None
    assert labeled.category is Category.SHOPPING


def test_compact_labels_respect_confidence(db_session: Session) -> None:
    tx = _tx(db_session, "UNKNOWN MERCHANT XYZ")

    def fake_complete(_messages):
        return {"labels": [{"index": 0, "category": "fuel", "confidence": 0.91}]}

    counts = apply_labels(db_session, Settings(llm_off=True), complete=fake_complete)
    assert counts["compact"] == 1
    labeled = tx_repo.get(db_session, tx.id or "")
    assert labeled is not None
    assert labeled.category is Category.FUEL
    assert labeled.label_source is LabelSource.MODEL
