from __future__ import annotations

from pathlib import Path

from finsca.ingest.pdf.text_extract import _is_password_error, extract_text


class PdfminerException(Exception):
    pass


class PDFPasswordIncorrect(Exception):
    def __str__(self) -> str:
        return ""


def test_wrapped_password_error_is_detected() -> None:
    exc = PdfminerException(PDFPasswordIncorrect())
    assert str(exc) == ""
    assert _is_password_error(exc)
    assert not _is_password_error(ValueError("broken xref"))


def test_extract_retries_stored_password(tmp_path: Path, monkeypatch) -> None:
    dest = tmp_path / "locked.pdf"
    dest.write_bytes(b"%PDF-1.4")
    calls: list[str] = []

    class FakePdf:
        pages = [type("P", (), {"extract_text": staticmethod(lambda: "hello")})()]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_open(_path, password=""):
        calls.append(password)
        if password != "secret":
            raise PdfminerException(PDFPasswordIncorrect())
        return FakePdf()

    monkeypatch.setattr("pdfplumber.open", fake_open)
    assert extract_text(dest, ["secret"]) == "hello"
    assert calls[0] == ""
    assert "secret" in calls
