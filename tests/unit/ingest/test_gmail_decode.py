from __future__ import annotations

import base64

from finsca.ingest.email.gmail_decode import decode_gmail_message, safe_stem


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_decode_gmail_plain_alert() -> None:
    payload = {
        "id": "abc123xyz",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "HDFC Bank <alerts@hdfcbank.net>"},
                {"name": "Subject", "value": "Rs.250.00 debited"},
                {"name": "Date", "value": "Sat, 01 Aug 2026 10:00:00 +0530"},
            ],
            "body": {"data": _b64("Rs.250.00 debited from a/c XX4521 on 01-08-26 to SWIGGY via UPI")},
        },
    }
    pulled = decode_gmail_message(payload)
    assert pulled.message_id == "abc123xyz"
    assert "hdfcbank.net" in pulled.record.address
    assert "SWIGGY" in pulled.record.body
    assert pulled.record.sent_at is not None
    assert "abc123xyz" in safe_stem(pulled.message_id, pulled.record.address)


def test_decode_nested_parts_and_pdf_attachment() -> None:
    payload = {
        "id": "att1",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "From", "value": "alerts@icicibank.com"}],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64("Your A/c XX4521 is credited with Rs.12500.00")},
                },
                {
                    "filename": "statement.pdf",
                    "mimeType": "application/pdf",
                    "body": {"data": _b64("%PDF-1.4 fake")},
                },
            ],
        },
    }
    pulled = decode_gmail_message(payload)
    assert "12500" in pulled.record.body
    assert len(pulled.attachments) == 1
    assert pulled.attachments[0].filename == "statement.pdf"
    assert pulled.attachments[0].data is not None
    assert pulled.attachments[0].attachment_id is None


def test_decode_pdf_attachment_id_without_inline_bytes() -> None:
    payload = {
        "id": "att2",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "From", "value": "alerts@hdfcbank.net"}],
            "parts": [
                {
                    "filename": "CC_Statement.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "ANGjdJxxx", "size": 12000},
                }
            ],
        },
    }
    pulled = decode_gmail_message(payload)
    assert len(pulled.attachments) == 1
    assert pulled.attachments[0].data is None
    assert pulled.attachments[0].attachment_id == "ANGjdJxxx"
    assert pulled.attachments[0].filename == "CC_Statement.pdf"
