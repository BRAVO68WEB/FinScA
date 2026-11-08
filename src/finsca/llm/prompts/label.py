"""Compact labeler. JSON only, one category from the list the user message sends."""

LABEL_SYSTEM = (
    "Classify each transaction into exactly one category from the list. "
    'Return JSON: {"labels": [{"index": 0, "category": "dining", "confidence": 0.9}]}. '
    "Use only categories named in the user message. Omit a row when you are unsure."
)
