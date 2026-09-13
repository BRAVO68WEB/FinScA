from __future__ import annotations

from finsca.ingest.pdf.axis import parse_axis
from finsca.ingest.pdf.generic import parse_generic
from finsca.ingest.pdf.hdfc import parse_hdfc
from finsca.ingest.pdf.icici import parse_icici
from finsca.ingest.pdf.idfc import parse_idfc
from finsca.ingest.types import ParsedBatch

_PARSERS = {
    "hdfc": parse_hdfc,
    "axis": parse_axis,
    "icici": parse_icici,
    "idfc": parse_idfc,
}


def parse_statement(text: str, bank_id: str | None) -> ParsedBatch:
    if bank_id and bank_id in _PARSERS:
        return _PARSERS[bank_id](text)
    institution = bank_id.upper() if bank_id else None
    return parse_generic(text, parser=bank_id or "generic", institution=institution)
