from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from finsca.core.enums import Category
from finsca.finance.labels import MerchantHint


@dataclass(frozen=True)
class Taxonomy:
    categories: tuple[Category, ...]
    merchants: tuple[MerchantHint, ...]


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    source = path or Path(__file__).with_name("labels.yaml")
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    categories = tuple(Category(item) for item in payload.get("categories", []))
    merchants = tuple(
        MerchantHint(match=str(item["match"]).upper(), category=Category(item["category"]))
        for item in payload.get("merchants", [])
    )
    return Taxonomy(categories=categories, merchants=merchants)
