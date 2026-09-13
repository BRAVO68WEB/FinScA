from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from finsca.ingest.alerts import AlertRecord
from finsca.ingest.errors import ParseError


def load_sms(path: Path) -> list[AlertRecord]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".xml":
            return _from_xml(path)
        if suffix == ".json":
            return _from_json(path)
        if suffix == ".csv":
            return _from_csv(path)
        raise ParseError(f"unsupported SMS dump: {path.suffix}")
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(f"could not read SMS dump: {exc}") from exc


def _from_xml(path: Path) -> list[AlertRecord]:
    root = ET.parse(path).getroot()
    records: list[AlertRecord] = []
    for node in root.iter("sms"):
        body = (node.attrib.get("body") or "").strip()
        if not body:
            continue
        records.append(
            AlertRecord(
                body=body,
                address=node.attrib.get("address") or "",
                sent_at=_millis(node.attrib.get("date")),
            )
        )
    return records


def _from_json(path: Path) -> list[AlertRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("sms") or payload.get("messages") or []
    records: list[AlertRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        body = str(item.get("body") or item.get("message") or item.get("text") or "").strip()
        if not body:
            continue
        records.append(
            AlertRecord(
                body=body,
                address=str(item.get("address") or item.get("from") or item.get("sender") or ""),
                sent_at=_parse_when(item.get("date") or item.get("timestamp") or item.get("datetime")),
            )
        )
    return records


def _from_csv(path: Path) -> list[AlertRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        records: list[AlertRecord] = []
        for raw in reader:
            row = {(key or "").strip().lower(): (value or "").strip() for key, value in raw.items()}
            body = row.get("body") or row.get("message") or row.get("text") or row.get("sms") or ""
            if not body:
                continue
            records.append(
                AlertRecord(
                    body=body,
                    address=row.get("address") or row.get("from") or row.get("sender") or "",
                    sent_at=_parse_when(row.get("date") or row.get("timestamp") or row.get("datetime")),
                )
            )
        return records


def _millis(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc)
    except ValueError:
        return None


def _parse_when(raw: object) -> datetime | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value > 10_000_000_000:
            value /= 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)
    text = str(raw)
    if text.isdigit():
        return _millis(text) if len(text) > 10 else datetime.fromtimestamp(int(text), tz=timezone.utc)
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
