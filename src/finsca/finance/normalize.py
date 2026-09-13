"""Description / merchant normalize."""


def normalize_description(raw: str) -> str:
    return " ".join(raw.split()).upper()
