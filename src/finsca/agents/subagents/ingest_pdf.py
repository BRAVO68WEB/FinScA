"""PDF ingest: extract, detect bank, parse. Used by the ingest pipeline."""

from pathlib import Path

from finsca.ingest.detect import detect_bank
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.text_extract import extract_text
from finsca.ingest.types import ParsedBatch


def parse_pdf(path: Path) -> ParsedBatch:
    text = extract_text(path)
    return parse_statement(text, detect_bank(text))
