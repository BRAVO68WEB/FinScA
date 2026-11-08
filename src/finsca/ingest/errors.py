class ParseError(ValueError):
    """A single inbox file cannot be ingested. Other files in the run continue."""


class SkipFile(Exception):
    """Inbox file is not a ledger source. Archive it; do not fail the run."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
