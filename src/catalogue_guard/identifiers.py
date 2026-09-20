import re
import unicodedata


def canonical_gtin(value):
    value = str(value).strip() if value is not None else ""
    if not re.fullmatch(r"(?:\d{8}|\d{12}|\d{13}|\d{14})", value, flags=re.ASCII):
        return None
    if not value.strip("0"):
        return None
    checksum = int(value[-1]) + sum(
        int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(value[-2::-1])
    )
    return value.zfill(14) if checksum % 10 == 0 else None


def name_tokens(value):
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    stopwords = {
        "de",
        "du",
        "des",
        "la",
        "le",
        "les",
        "au",
        "aux",
        "et",
        "en",
        "avec",
        "a",
        "d",
        "the",
        "of",
        "g",
        "kg",
        "ml",
        "l",
    }
    return {word for word in re.findall(r"[a-z]{3,}", text) if word not in stopwords}


def name_conflict(left, right):
    a, b = name_tokens(left), name_tokens(right)
    return bool(a and b and not a.intersection(b))


def recall_identifiers(value):
    raw = " ".join(str(part) for part in value) if isinstance(value, list) else str(value or "")
    for block in raw.split("|"):
        block = block.strip()
        candidate = block.split()[0] if block else ""
        yield candidate, canonical_gtin(candidate), block
