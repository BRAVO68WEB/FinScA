from __future__ import annotations

from pathlib import Path

import pytest

from finsca.config.settings import Settings
from finsca.core.enums import SourceKind
from finsca.ingest.dispatch import parse_inbox_file
from finsca.ingest.errors import SkipFile


def test_marketing_email_is_skipped(tmp_path: Path) -> None:
    dest = tmp_path / "offers.eml"
    dest.write_text("From: offers@sbicard.com\nSubject: Flexipay EMI\n\nConvert your spends!\n")
    with pytest.raises(SkipFile, match="no transaction alert"):
        parse_inbox_file(dest, SourceKind.EMAIL, Settings(data_dir=tmp_path))


def test_kfs_pdf_is_skipped_by_name(tmp_path: Path) -> None:
    dest = tmp_path / "19f8_donotreply_bobcard.in_CreditCardKFS.pdf"
    dest.write_bytes(b"%PDF-1.4")
    with pytest.raises(SkipFile, match="not a bank/card statement"):
        parse_inbox_file(dest, SourceKind.PDF, Settings(data_dir=tmp_path))
