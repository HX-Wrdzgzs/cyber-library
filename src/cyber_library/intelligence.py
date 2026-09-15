from .models import Analysis, BookRecord

def catalog_analysis(record: BookRecord) -> Analysis:
    work, edition = record.work, record.edition
    title=(work.title if work else edition.title).strip()
    subjects=list(dict.fromkeys((work.subjects if work else [])[:12]))
    parts=[]
    if title: parts.append(f"《{title}》是一条已解析的图书目录记录。")
    if subjects: parts.append("现有主题元数据包括："+"、".join(subjects[:6])+"。")
    if edition.publishers: parts.append("当前版本的出版者信息："+"、".join(edition.publishers[:3])+"。")
    warnings=["This L1 analysis uses catalog metadata only.","No chapter-level or full-text claims are made."]
    if not subjects: warnings.append("No subject metadata was available; topic inference was omitted.")
    return Analysis(level="L1",brief="".join(parts) or None,tags=subjects,outline=[],
                    confidence=0.65 if subjects else 0.35,
                    sources=list(dict.fromkeys(record.analysis.sources+edition.source_refs)),
                    warnings=warnings)
