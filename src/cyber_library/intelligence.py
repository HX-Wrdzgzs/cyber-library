from __future__ import annotations

from .models import Analysis, BookRecord


def catalog_analysis(record: BookRecord) -> Analysis:
    """Generate safe L1 output from catalog metadata only."""
    work, edition = record.work, record.edition
    title = (work.title if work else edition.title).strip()
    authors = (work.authors if work else [])[:6]
    subjects = list(dict.fromkeys((work.subjects if work else [])[:16]))

    parts: list[str] = []
    if title:
        parts.append(f"《{title}》是一条已解析的图书目录记录。")
    if authors:
        parts.append("作者信息：" + "、".join(authors) + "。")
    if subjects:
        parts.append("现有主题元数据包括：" + "、".join(subjects[:6]) + "。")
    if edition.publishers:
        parts.append("当前版本的出版者信息：" + "、".join(edition.publishers[:3]) + "。")

    brief = "".join(parts) or None
    mindmap = None
    if title and subjects:
        mindmap = {
            "name": title,
            "relation": "catalog-subjects",
            "children": [{"name": subject, "relation": "subject", "children": []} for subject in subjects[:10]],
        }

    warnings = [
        "L1 analysis uses catalog metadata only.",
        "Detailed interpretation, table of contents, chapter summaries and structural outline were not generated without supporting sources.",
    ]
    if not subjects:
        warnings.append("No subject metadata was available; topic inference was omitted.")

    return Analysis(
        level="L1",
        brief=brief,
        summary=brief,
        detailed=None,
        tags=subjects,
        table_of_contents=[],
        outline=[],
        mindmap=mindmap,
        confidence=0.65 if subjects else 0.35,
        sources=list(dict.fromkeys(record.analysis.sources + edition.source_refs)),
        warnings=warnings,
    )
