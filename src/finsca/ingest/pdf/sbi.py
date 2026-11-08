"""SBI savings statement parser."""

from __future__ import annotations

from finsca.ingest.pdf.generic import parse_generic_lines
from finsca.ingest.pdf.header import batch_from, parse_header
from finsca.ingest.types import ParsedBatch


def parse_sbi(text: str) -> ParsedBatch:
    header = parse_header(text, institution="SBI")
    lines, warnings = parse_generic_lines(text)
    return batch_from("sbi", header, lines, warnings)
