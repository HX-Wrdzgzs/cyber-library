from __future__ import annotations

from .models import BookRecord

def build_knowledge_graph(record: BookRecord, related: list[dict] | None = None) -> dict:
    work=record.work; edition=record.edition; title=(work.title if work else edition.title) or "Untitled"; work_id=work.id if work else (edition.work_id or edition.id)
    nodes={}; edges=[]
    def add_node(node_id,label,kind,**extra):
        if node_id not in nodes:nodes[node_id]={"id":node_id,"label":label,"kind":kind,**extra}
    def add_edge(source,target,relation):edges.append({"source":source,"target":target,"relation":relation})
    add_node(work_id,title,"work")
    if work:
        for author in work.authors[:12]:
            node_id="author:"+author.casefold(); add_node(node_id,author,"author"); add_edge(work_id,node_id,"written_by")
        for category in work.categories[:8]:
            node_id="category:"+category.casefold(); add_node(node_id,category,"category"); add_edge(work_id,node_id,"classified_as")
        for subject in work.subjects[:24]:
            node_id="subject:"+subject.casefold(); add_node(node_id,subject,"subject"); add_edge(work_id,node_id,"has_subject")
            for category in work.categories[:3]:
                category_id="category:"+category.casefold(); add_node(category_id,category,"category"); add_edge(node_id,category_id,"belongs_to")
    for publisher in edition.publishers[:8]:
        node_id="publisher:"+publisher.casefold(); add_node(node_id,publisher,"publisher"); add_edge(work_id,node_id,"published_by")
    if edition.publish_date:
        year=str(edition.publish_date)[:4]
        if year.isdigit():
            node_id="year:"+year; add_node(node_id,year,"year"); add_edge(work_id,node_id,"published_in")
    for item in (related or [])[:16]:
        related_id=item.get("work_id") or item.get("edition_id")
        if not related_id or related_id==work_id:continue
        add_node(related_id,item.get("title") or "Untitled","related_work",isbn=item.get("isbn"),categories=item.get("categories") or []); add_edge(work_id,related_id,"related")
    return {"root":work_id,"nodes":list(nodes.values()),"edges":edges}
