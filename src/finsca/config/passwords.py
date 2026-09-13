"""Local PDF password store. File lives under data/ and is gitignored."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from finsca.config.settings import Settings


@dataclass(frozen=True)
class PasswordEntry:
    password: str
    match: str | None = None


def store_path(settings: Settings | None = None) -> Path:
    root = settings.data_dir if settings else Settings().data_dir
    return root / "pdf_passwords.yaml"


def load_store(path: Path | None = None) -> list[PasswordEntry]:
    dest = path or store_path()
    if not dest.exists():
        return []
    payload = yaml.safe_load(dest.read_text(encoding="utf-8")) or {}
    raw = payload.get("passwords", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        return []
    entries: list[PasswordEntry] = []
    for item in raw:
        if isinstance(item, str) and item:
            entries.append(PasswordEntry(password=item))
        elif isinstance(item, dict) and item.get("password"):
            match = item.get("match")
            entries.append(PasswordEntry(password=str(item["password"]), match=str(match) if match else None))
    return entries


def save_store(entries: list[PasswordEntry], path: Path | None = None) -> Path:
    dest = path or store_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "passwords": [
            {"password": item.password, **({"match": item.match} if item.match else {})}
            for item in entries
        ]
    }
    dest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return dest


def add_password(password: str, *, match: str | None = None, path: Path | None = None) -> list[PasswordEntry]:
    entries = load_store(path)
    entry = PasswordEntry(password=password, match=match.lower() if match else None)
    if entry not in entries:
        entries.append(entry)
        save_store(entries, path)
    return entries


def candidates_for(filename: str, entries: list[PasswordEntry], extra: str | None = None) -> list[str]:
    name = filename.lower()
    matched = [item.password for item in entries if item.match and item.match.lower() in name]
    general = [item.password for item in entries if not item.match]
    ordered: list[str] = []
    for password in [*matched, *general, *([extra] if extra else [])]:
        if password and password not in ordered:
            ordered.append(password)
    return ordered


def mask(password: str) -> str:
    if len(password) <= 2:
        return "*" * len(password)
    return "*" * (len(password) - 2) + password[-2:]
