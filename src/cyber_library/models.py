from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(slots=True)
class Provenance:
    source: str; source_id: str | None = None; url: str | None = None; retrieved_at: str | None = None; license: str | None = None

@dataclass(slots=True)
class EvidenceItem:
    kind: str; text: str; source_ref: str; title: str | None = None; url: str | None = None

@dataclass(slots=True)
class Work:
    id: str; title: str; authors: list[str] = field(default_factory=list); subjects: list[str] = field(default_factory=list); description: str | None = None; first_sentence: str | None = None; categories: list[str] = field(default_factory=list); source_refs: list[str] = field(default_factory=list)

@dataclass(slots=True)
class Edition:
    id: str; work_id: str | None; title: str; language: str | None = None; publishers: list[str] = field(default_factory=list); publish_date: str | None = None; page_count: int | None = None; identifiers: dict[str, list[str]] = field(default_factory=dict); cover_url: str | None = None; table_of_contents: list[str] = field(default_factory=list); physical_format: str | None = None; source_refs: list[str] = field(default_factory=list)

@dataclass(slots=True)
class Analysis:
    level: str = "L0"; brief: str | None = None; summary: str | None = None; detailed: str | None = None; tags: list[str] = field(default_factory=list); categories: list[str] = field(default_factory=list); themes: list[str] = field(default_factory=list); key_points: list[str] = field(default_factory=list); table_of_contents: list[str] = field(default_factory=list); outline: list[str] = field(default_factory=list); chapter_summaries: list[dict[str, str]] = field(default_factory=list); mindmap: dict[str, Any] | None = None; confidence: float = 0.0; sources: list[str] = field(default_factory=list); warnings: list[str] = field(default_factory=list); generated_at: str | None = None; model: str | None = None

@dataclass(slots=True)
class BookRecord:
    work: Work | None; edition: Edition; analysis: Analysis = field(default_factory=Analysis); provenance: list[Provenance] = field(default_factory=list); evidence: list[EvidenceItem] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)
