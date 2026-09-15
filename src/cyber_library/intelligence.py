from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone

from .llm import LLMClient, LLMError
from .models import Analysis, BookRecord
from .taxonomy import classify, normalize_tags

_STOPWORDS = {"the","and","for","with","that","this","from","into","about","their","there","which","have","has","had","were","was","are","but","not","you","your","our","they","them","his","her","its","can","may","book","chapter","edition","introduction","preface","一个","一种","以及","我们","你们","他们","这些","那些","这个","那个","可以","可能","进行","通过","对于","关于","其中","因为","所以","但是","本书","作者","章节","内容","部分","主要"}

def _now(): return datetime.now(timezone.utc).isoformat()
def _sentences(text):
    text=re.sub(r"\s+"," ",text).strip()
    if not text:return []
    return [p.strip() for p in re.split(r"(?<=[。！？!?\.])\s+|(?<=[。！？!?])",text) if len(p.strip())>=12]
def _tokens(text):
    english=re.findall(r"[A-Za-z][A-Za-z0-9'_-]{2,}",text.casefold()); cjk=[]
    for seq in re.findall(r"[\u3400-\u9fff]{2,}",text):
        if len(seq)<=4:cjk.append(seq)
        else:
            for width in (2,3,4):
                for i in range(len(seq)-width+1):cjk.append(seq[i:i+width])
    return [t for t in english+cjk if t not in _STOPWORDS and len(t)>1]
def extractive_summary(text,max_sentences=5,max_chars=1800):
    sentences=_sentences(text)
    if not sentences:return re.sub(r"\s+"," ",text).strip()[:max_chars]
    freq=Counter(_tokens(text))
    if not freq:return " ".join(sentences[:max_sentences])[:max_chars]
    scores=[]
    for i,sentence in enumerate(sentences):
        tokens=_tokens(sentence)
        if tokens:scores.append((sum(freq[t] for t in tokens)/math.sqrt(max(1,len(tokens))),i,sentence))
    selected=sorted(sorted(scores,reverse=True)[:max_sentences],key=lambda x:x[1])
    return " ".join(x[2] for x in selected)[:max_chars].strip()
def keywords(text,limit=16):
    counts=Counter(_tokens(text)); ordered=sorted(counts.items(),key=lambda x:(x[1],len(x[0])),reverse=True); out=[]
    for term,count in ordered:
        if count<2 and len(text)>1000:continue
        if any(term.casefold()==x.casefold() for x in out):continue
        out.append(term)
        if len(out)>=limit:break
    return out
def _mindmap(title,categories,themes,outline):
    children=[]
    if categories:children.append({"name":"分类","relation":"category","children":[{"name":x,"relation":"category","children":[]} for x in categories]})
    if themes:children.append({"name":"主题","relation":"theme","children":[{"name":x,"relation":"theme","children":[]} for x in themes[:12]]})
    if outline:children.append({"name":"结构","relation":"structure","children":[{"name":x,"relation":"section","children":[]} for x in outline[:16]]})
    return {"name":title or "Untitled","relation":"work","children":children}
def catalog_analysis(record):
    work,edition=record.work,record.edition; title=((work.title if work else edition.title) or "").strip(); authors=(work.authors if work else [])[:6]; subjects=normalize_tags(work.subjects if work else [],24); categories=(work.categories if work and work.categories else classify(subjects,title)) if work else classify(subjects,title)
    parts=[]
    if title:parts.append(f"《{title}》是一条已解析的图书目录记录。")
    if authors:parts.append("作者信息："+"、".join(authors)+"。")
    if subjects:parts.append("目录主题包括："+"、".join(subjects[:8])+"。")
    if edition.publishers:parts.append("当前版本出版者："+"、".join(edition.publishers[:3])+"。")
    brief="".join(parts) or None; warnings=["当前解读只使用目录元数据；没有把未读取的正文内容当作事实。"]
    if not subjects:warnings.append("缺少主题元数据，因此没有对具体内容作强推断。")
    return Analysis(level="L1",brief=brief,summary=brief,detailed=None,tags=subjects,categories=categories,themes=subjects[:10],key_points=[],table_of_contents=list(edition.table_of_contents),outline=list(edition.table_of_contents[:40]),mindmap=_mindmap(title,categories,subjects[:10],edition.table_of_contents[:40]),confidence=.65 if subjects else .35,sources=list(dict.fromkeys(record.analysis.sources+edition.source_refs)),warnings=warnings,generated_at=_now(),model="deterministic/catalog")
def _evidence_payload(record,max_chars=32000):
    parts=[]; used=0
    for item in record.evidence:
        text=item.text.strip()
        if not text:continue
        remaining=max_chars-used
        if remaining<=0:break
        block=f"[{item.title or item.kind} | {item.source_ref}]\n{text[:remaining]}"; parts.append(block); used+=len(block)
    return "\n\n".join(parts)
def _list(value,limit=32):
    if not isinstance(value,list):return []
    out=[]
    for item in value:
        if isinstance(item,str) and item.strip():out.append(re.sub(r"\s+"," ",item).strip())
        if len(out)>=limit:break
    return list(dict.fromkeys(out))
def _merge_llm(base,raw,model):
    for field in ("brief","summary","detailed"):
        value=raw.get(field)
        if isinstance(value,str) and value.strip():setattr(base,field,value.strip())
    for field,limit in (("tags",32),("themes",16),("key_points",24),("outline",80)):
        values=_list(raw.get(field),limit)
        if values:setattr(base,field,values)
    toc=_list(raw.get("table_of_contents"),500)
    if toc and not base.table_of_contents:base.table_of_contents=toc
    if isinstance(raw.get("chapter_summaries"),list):
        clean=[]
        for item in raw["chapter_summaries"][:80]:
            if isinstance(item,dict) and isinstance(item.get("title"),str) and isinstance(item.get("summary"),str) and item["title"].strip() and item["summary"].strip():clean.append({"title":item["title"].strip(),"summary":item["summary"].strip()})
        if clean:base.chapter_summaries=clean
    base.model=model; return base
def source_analysis(record,llm=None):
    if not record.evidence and not record.edition.table_of_contents:return catalog_analysis(record)
    work,edition=record.work,record.edition; title=(work.title if work else edition.title) or edition.title; subjects=normalize_tags(work.subjects if work else [],24); categories=work.categories if work and work.categories else classify(subjects,title,work.description if work and work.description else ""); evidence_text=_evidence_payload(record); toc=list(edition.table_of_contents)
    if not toc:
        for item in record.evidence:
            if item.kind=="table_of_contents":toc=[x.strip() for x in item.text.splitlines() if x.strip()][:500]; break
    summary=extractive_summary(evidence_text,5,1800); brief=extractive_summary(evidence_text,2,700); key_points=_sentences(summary)[:8]; themes=normalize_tags(subjects+keywords(evidence_text,12),16); outline=toc[:80]; detailed=(summary or "")+("\n\n现有目录显示本书结构包含："+"、".join(toc[:12])+("等。" if len(toc)>12 else "。") if toc else ""); detailed=detailed or None; sources=list(dict.fromkeys([x.source_ref for x in record.evidence]+edition.source_refs+(work.source_refs if work else [])))
    base=Analysis(level="L2",brief=brief,summary=summary,detailed=detailed,tags=normalize_tags(subjects+themes,32),categories=categories,themes=themes,key_points=key_points,table_of_contents=toc,outline=outline,mindmap=_mindmap(title,categories,themes,outline),confidence=min(.92,.58+.06*min(len(record.evidence),5)+(.08 if toc else 0)),sources=sources,warnings=["详细解读严格限制在已取得的简介、目录、摘录或其他来源证据内；未读取的正文不会被补写。"],generated_at=_now(),model="deterministic/source-backed")
    if llm:
        system="你是图书知识分析器。只允许使用用户提供的元数据和证据，不得凭记忆补充书中事实。如果证据不支持某个判断，就省略。返回 JSON：brief, summary, detailed, tags, themes, key_points, outline。"
        user=f"书名：{title}\n作者：{'、'.join(work.authors if work else [])}\n主题：{'、'.join(subjects)}\n目录：{jsonish(toc)}\n\n证据：\n{evidence_text}"
        try:base=_merge_llm(base,llm.complete_json(system,user),llm.model_name); base.warnings.append("LLM 输出已被限制为来源证据内的结构化分析。")
        except LLMError as exc:base.warnings.append(f"LLM 不可用，已保留确定性分析：{exc}")
        base.mindmap=_mindmap(title,base.categories,base.themes,base.outline)
    return base
def jsonish(values):return " / ".join(values[:100]) if values else "(none)"
def _chunk_text(text,target=18000):
    paragraphs=[p.strip() for p in re.split(r"\n\s*\n",text) if p.strip()]; chunks=[]; current=[]; size=0
    if not paragraphs:return [text]
    for p in paragraphs:
        if current and size+len(p)>target:chunks.append("\n\n".join(current)); current=[]; size=0
        current.append(p); size+=len(p)
    if current:chunks.append("\n\n".join(current))
    return chunks
def _section_summaries(text,headings):
    if headings:
        positions=[]; lower=text.casefold(); cursor=0
        for heading in headings[:120]:
            pos=lower.find(heading.casefold(),cursor)
            if pos<0:pos=lower.find(heading.casefold())
            if pos>=0:positions.append((pos,heading)); cursor=pos+len(heading)
        positions.sort()
        if positions:
            out=[]
            for i,(start,heading) in enumerate(positions):
                end=positions[i+1][0] if i+1<len(positions) else len(text); summary=extractive_summary(text[start:end],3,900)
                if summary:out.append({"title":heading,"summary":summary})
            if out:return out[:80]
    out=[]
    for i,chunk in enumerate(_chunk_text(text)[:80],1):
        summary=extractive_summary(chunk,3,900)
        if summary:out.append({"title":f"Section {i}","summary":summary})
    return out
def full_text_analysis(record,text,headings,rights,source_ref,llm=None):
    if len(text.strip())<100:raise ValueError("full text is too short")
    work,edition=record.work,record.edition; title=(work.title if work else edition.title) or edition.title; subjects=normalize_tags(work.subjects if work else [],24); categories=work.categories if work and work.categories else classify(subjects,title,text[:20000]); chapter_summaries=_section_summaries(text,headings or []); global_summary=extractive_summary(text,8,3200); brief=extractive_summary(text,2,700); text_keywords=keywords(text,24); themes=normalize_tags(subjects+text_keywords,18); outline=list(headings or [x["title"] for x in chapter_summaries])[:100]; key_points=_sentences(global_summary)[:12]; detailed=global_summary
    if chapter_summaries:detailed+="\n\n结构性阅读："+"；".join(f"{x['title']}：{x['summary'][:220]}" for x in chapter_summaries[:12])
    sources=list(dict.fromkeys([source_ref]+edition.source_refs+(work.source_refs if work else [])))
    base=Analysis(level="L3",brief=brief,summary=global_summary,detailed=detailed,tags=normalize_tags(subjects+text_keywords,32),categories=categories,themes=themes,key_points=key_points,table_of_contents=list(headings or edition.table_of_contents)[:500],outline=outline,chapter_summaries=chapter_summaries,mindmap=_mindmap(title,categories,themes,outline),confidence=.94,sources=sources,warnings=[f"全文分析基于调用方声明的内容权限：{rights}。","Cyber Library 默认不保存原始全文，只保留分析结果和内容哈希/来源元数据。"],generated_at=_now(),model="deterministic/full-text")
    if llm:
        digest="\n\n".join(f"[{x['title']}]\n{x['summary']}" for x in chapter_summaries[:80]); system="你是严谨的图书全文分析器。只能依据提供材料总结，禁止引用不存在的章节、观点或情节。返回 JSON：brief, summary, detailed, tags, themes, key_points, outline, chapter_summaries。"; user=f"书名：{title}\n作者：{'、'.join(work.authors if work else [])}\n目录/标题：{jsonish(outline)}\n全书抽取摘要：{global_summary}\n\n分段摘要：\n{digest[:120000]}"
        try:base=_merge_llm(base,llm.complete_json(system,user,max_tokens=4000),llm.model_name); base.warnings.append("LLM 综合使用了覆盖全文的分段摘要，而不是只截取书首。")
        except LLMError as exc:base.warnings.append(f"LLM 不可用，已保留本地全文分析：{exc}")
        base.mindmap=_mindmap(title,base.categories,base.themes,base.outline)
    return base
def analyze_record(record,llm=None,mode="auto"):
    mode=(mode or "auto").lower()
    if mode in {"none","off","0","false"}:return record.analysis
    if mode in {"catalog","l1"}:return catalog_analysis(record)
    if mode in {"source","l2"}:return source_analysis(record,llm)
    if mode=="auto":return source_analysis(record,llm) if record.evidence or record.edition.table_of_contents else catalog_analysis(record)
    raise ValueError(f"unknown analysis mode: {mode}")
