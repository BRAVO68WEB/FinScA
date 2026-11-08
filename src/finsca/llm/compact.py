"""Cheap structured labeling. The complete() hook is injected so tests stay offline."""

from __future__ import annotations

from dataclasses import dataclass

from finsca.core.enums import Category
from finsca.llm.prompts.label import LABEL_SYSTEM
from finsca.llm.redaction import redact


@dataclass(frozen=True)
class LabelGuess:
    index: int
    category: Category
    confidence: float


def suggest_labels(
    descriptions: list[str],
    categories: tuple[Category, ...] | list[Category],
    *,
    complete,
    min_confidence: float,
) -> list[LabelGuess]:
    if not descriptions:
        return []
    allowed = {item.value for item in categories}
    payload = complete(
        [
            {"role": "system", "content": LABEL_SYSTEM},
            {
                "role": "user",
                "content": (
                    "categories: " + ", ".join(sorted(allowed)) + "\n"
                    + "\n".join(f"{idx}. {redact(text)}" for idx, text in enumerate(descriptions))
                ),
            },
        ]
    )
    guesses: list[LabelGuess] = []
    for item in payload.get("labels", []):
        try:
            index = int(item["index"])
            category = Category(str(item["category"]))
            confidence = float(item.get("confidence", 0))
        except (KeyError, TypeError, ValueError):
            continue
        if index < 0 or index >= len(descriptions):
            continue
        if category.value not in allowed or confidence < min_confidence:
            continue
        guesses.append(LabelGuess(index=index, category=category, confidence=confidence))
    return guesses
