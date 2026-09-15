from __future__ import annotations
import re

class InvalidISBN(ValueError):
    pass

def compact(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", value or "").upper()

def is_valid_isbn10(value: str) -> bool:
    value = compact(value)
    if len(value) != 10 or not re.fullmatch(r"\d{9}[\dX]", value):
        return False
    return sum((10-i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(value)) % 11 == 0

def is_valid_isbn13(value: str) -> bool:
    value = compact(value)
    if len(value) != 13 or not value.isdigit():
        return False
    total = sum((1 if i % 2 == 0 else 3) * int(ch) for i, ch in enumerate(value[:12]))
    return (10 - total % 10) % 10 == int(value[-1])

def isbn10_to_isbn13(value: str) -> str:
    value = compact(value)
    if not is_valid_isbn10(value):
        raise InvalidISBN(f"Invalid ISBN-10: {value}")
    body = "978" + value[:9]
    total = sum((1 if i % 2 == 0 else 3) * int(ch) for i, ch in enumerate(body))
    return body + str((10-total%10)%10)

def normalize_isbn(value: str) -> str:
    value = compact(value)
    if len(value) == 10:
        return isbn10_to_isbn13(value)
    if len(value) == 13 and is_valid_isbn13(value):
        return value
    raise InvalidISBN(f"Invalid ISBN: {value}")
