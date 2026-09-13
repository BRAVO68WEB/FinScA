from __future__ import annotations

from finsca.core.enums import (
    AccountType,
    Category,
    Channel,
    EmiStatus,
    GstSource,
    IncomeReview,
    Intent,
    LabelSource,
    LoanStatus,
    MonthSource,
    SourceKind,
)
from finsca.core.models import Account, AccountMonth, EmiOccurrence, Loan, Transaction
from finsca.core.money import from_paise
from finsca.db import schema as tables


def account_from_row(row: tables.Account) -> Account:
    credit = from_paise(row.credit_limit_paise) if row.credit_limit_paise is not None else None
    return Account(
        id=row.id,
        display_name=row.display_name,
        institution=row.institution,
        type=AccountType(row.type),
        last4=row.last4,
        upi_vpas=list(row.upi_vpas or []),
        holder_aliases=list(row.holder_aliases or []),
        currency=row.currency,
        is_own=row.is_own,
        credit_limit=credit,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def month_from_row(row: tables.AccountMonth) -> AccountMonth:
    return AccountMonth(
        id=row.id,
        account_id=row.account_id,
        year=row.year,
        month=row.month,
        opening=from_paise(row.opening_paise),
        closing=from_paise(row.closing_paise),
        source=MonthSource(row.source),
        statement_id=row.statement_id,
    )


def transaction_from_row(row: tables.Transaction) -> Transaction:
    gst_amount = from_paise(row.gst_amount_paise) if row.gst_amount_paise is not None else None
    return Transaction(
        id=row.id,
        account_id=row.account_id,
        posted_at=row.posted_at,
        value_date=row.value_date,
        amount=from_paise(row.amount_paise),
        currency=row.currency,
        description_raw=row.description_raw,
        description_norm=row.description_norm,
        counterparty=row.counterparty,
        merchant=row.merchant,
        channel=Channel(row.channel),
        category=Category(row.category) if row.category else None,
        subcategory=row.subcategory,
        intent=Intent(row.intent),
        gst_rate=row.gst_rate,
        gst_amount=gst_amount,
        gst_source=GstSource(row.gst_source),
        source_kind=SourceKind(row.source_kind),
        source_ref=row.source_ref,
        content_hash=row.content_hash,
        ingest_run_id=row.ingest_run_id,
        duplicate_of_id=row.duplicate_of_id,
        self_transfer_group_id=row.self_transfer_group_id,
        exclude_from_cashflow=row.exclude_from_cashflow,
        label_source=LabelSource(row.label_source) if row.label_source else None,
        label_confidence=row.label_confidence,
        income_review=IncomeReview(row.income_review),
    )


def loan_from_row(row: tables.Loan) -> Loan:
    return Loan(
        id=row.id,
        name=row.name,
        lender=row.lender,
        principal=from_paise(row.principal_paise),
        emi=from_paise(row.emi_paise),
        emi_day=row.emi_day,
        tenure_months=row.tenure_months,
        rate_bps=row.rate_bps,
        start_date=row.start_date,
        status=LoanStatus(row.status),
        account_id=row.account_id,
    )


def occurrence_from_row(row: tables.EmiOccurrence) -> EmiOccurrence:
    return EmiOccurrence(
        id=row.id,
        loan_id=row.loan_id,
        due_date=row.due_date,
        expected=from_paise(row.expected_paise),
        status=EmiStatus(row.status),
        transaction_id=row.transaction_id,
    )
