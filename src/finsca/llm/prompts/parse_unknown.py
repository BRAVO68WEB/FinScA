"""Last-resort parse of a redacted statement."""

PARSE_UNKNOWN_SYSTEM = (
    "Extract transactions from this redacted bank statement. "
    'Return JSON: {"lines": [{"posted_at": "YYYY-MM-DD", "amount": "-10.00", '
    '"description": "MERCHANT", "last4": "4521"}]}. '
    "Amounts are signed decimal strings, debit negative. "
    "Skip lines you cannot read. Do not guess an account number."
)
