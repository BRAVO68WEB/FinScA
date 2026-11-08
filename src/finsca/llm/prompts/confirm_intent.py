"""Income versus transfer for a credit the rules did not decide."""

CONFIRM_INTENT_SYSTEM = (
    "Decide whether this credit is income or a transfer between accounts. "
    'Return JSON: {"intent": "income" | "transfer" | "unknown", "confidence": 0.0}. '
    "Use unknown when the narration does not say. Do not invent a payer."
)
