class ParseError(ValueError):
    """A single inbox file cannot be ingested. Other files in the run continue."""
