from __future__ import annotations

import pytest

from finsca.ingest.email.gmail_api import BANK_FILTER, search_query


def test_months_wraps_default_filter() -> None:
    q = search_query(months=6)
    assert q.startswith("newer_than:6m (")
    assert "hdfcbank.net" in q


def test_custom_query_gets_months() -> None:
    q = search_query(months=3, extra="from:alerts@hdfcbank.net")
    assert q == "newer_than:3m (from:alerts@hdfcbank.net)"


def test_query_with_existing_window_is_left_alone() -> None:
    q = search_query(months=6, extra="newer_than:10d from:cred.club")
    assert q == "newer_than:10d from:cred.club"


def test_months_must_be_positive() -> None:
    with pytest.raises(ValueError):
        search_query(months=0)
    assert BANK_FILTER
