"""Pure merchant / taxonomy matching."""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsca.core.enums import Category
from finsca.finance.normalize import normalize_description


@dataclass(frozen=True)
class MerchantHint:
    match: str
    category: Category


def match_merchant(description: str, merchants: tuple[MerchantHint, ...] | list[MerchantHint]) -> Category | None:
    blob = normalize_description(description)
    for hint in merchants:
        if re.search(rf"\b{re.escape(hint.match)}\b", blob):
            return hint.category
    return None
