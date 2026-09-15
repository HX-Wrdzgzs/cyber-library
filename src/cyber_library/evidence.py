from __future__ import annotations

import re
from typing import Any

from .models import EvidenceItem


def text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip(); return text or None
    if isinstance(value, dict):
        for key in ("value", "text", "content"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def toc_titles(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            title = item
        elif isinstance(item, dict):
            title = item.get("title") or item.get("label") or item.get("name")
        else:
            continue
        if title:
            title = re.sub(r"\s+", " ", str(title)).strip()
            if title and title not in out:
                out.append(title)
    return out[:500]


def openlibrary_evidence(work_raw: dict[str, Any] | None, edition_raw: dict[str, Any] | None, work_ref: str | None = None, edition_ref: str | None = None) -> list[EvidenceItem]:
    work_raw = work_raw or {}; edition_raw = edition_raw or {}; evidence: list[EvidenceItem] = []
    description = text_value(work_raw.get("description")) or text_value(edition_raw.get("description"))
    if description: evidence.append(EvidenceItem("description", description, work_ref or edition_ref or "openlibrary"))
    first_sentence = text_value(work_raw.get("first_sentence")) or text_value(edition_raw.get("first_sentence"))
    if first_sentence: evidence.append(EvidenceItem("first_sentence", first_sentence, work_ref or edition_ref or "openlibrary"))
    notes = text_value(edition_raw.get("notes")) or text_value(work_raw.get("notes"))
    if notes: evidence.append(EvidenceItem("notes", notes, edition_ref or work_ref or "openlibrary"))
    raw_excerpts = work_raw.get("excerpts") or edition_raw.get("excerpts") or []
    if isinstance(raw_excerpts, list):
        for item in raw_excerpts[:12]:
            text = text_value(item)
            if text: evidence.append(EvidenceItem("excerpt", text, work_ref or edition_ref or "openlibrary"))
    toc = toc_titles(edition_raw.get("table_of_contents") or work_raw.get("table_of_contents"))
    if toc: evidence.append(EvidenceItem("table_of_contents", "\n".join(toc), edition_ref or work_ref or "openlibrary", title="Table of contents"))
    seen: set[tuple[str, str]] = set(); out: list[EvidenceItem] = []
    for item in evidence:
        key = (item.kind, item.text)
        if key not in seen:
            seen.add(key); out.append(item)
    return out
