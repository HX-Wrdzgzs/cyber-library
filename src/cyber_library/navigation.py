from __future__ import annotations

import json
import re
from collections import Counter

from .database import CatalogDB, _eid, _wid
from .taxonomy import normalize_subject, normalize_subjects


def _items(value: str | None) -> list[str]:
    try:
        raw = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(x) for x in raw if isinstance(x, (str, int, float))]


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(?<!\d)(1[0-9]{3}|20[0-9]{2}|21[0-9]{2})(?!\d)", str(value))
    return int(match.group(1)) if match else None


def concept_graph(catalog: CatalogDB, subject: str, limit: int = 40) -> dict:
    requested = subject.strip()
    if not requested:
        raise ValueError("subject is required")
    canonical = normalize_subject(requested)
    limit = max(1, min(int(limit), 200))
    needle = canonical.casefold()
    with catalog._lock:
        rows = catalog.db.execute(
            "SELECT id,title,subjects,categories FROM works WHERE subjects LIKE ? OR title LIKE ? ORDER BY title LIMIT ?",
            (f"%{canonical}%", f"%{requested}%", limit * 4),
        ).fetchall()

    selected = []
    co_subjects: Counter[str] = Counter()
    for row in rows:
        subjects = normalize_subjects(_items(row["subjects"]), 128)
        title = str(row["title"] or "")
        if needle not in title.casefold() and not any(needle in x.casefold() for x in subjects):
            continue
        selected.append({"id": str(row["id"]), "title": title, "subjects": subjects, "categories": _items(row["categories"])})
        for value in subjects:
            if value.casefold() != needle:
                co_subjects[value] += 1
        if len(selected) >= limit:
            break

    root = f"concept:{needle}"
    nodes = [{"id": root, "kind": "concept", "label": canonical}]
    edges = []
    works = []
    for work in selected:
        wid = _wid(work["id"])
        nodes.append({"id": wid, "kind": "work", "label": work["title"], "categories": work["categories"]})
        edges.append({"source": root, "target": wid, "kind": "concept-work"})
        works.append({"work_id": wid, "title": work["title"], "subjects": work["subjects"], "categories": work["categories"]})

    for value, count in co_subjects.most_common(24):
        sid = f"subject:{value.casefold()}"
        nodes.append({"id": sid, "kind": "subject", "label": value, "weight": count})
        edges.append({"source": root, "target": sid, "kind": "co-subject", "weight": count})

    return {"kind": "concept_graph", "query": requested, "canonical_query": canonical, "root": root, "nodes": nodes, "edges": edges, "works": works}


def author_timeline(catalog: CatalogDB, name: str, limit: int = 100) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("author name is required")
    limit = max(1, min(int(limit), 500))
    with catalog._lock:
        authors = catalog.db.execute(
            "SELECT id,name FROM authors WHERE name = ? COLLATE NOCASE ORDER BY name LIMIT 20", (name,)
        ).fetchall()
        if not authors:
            authors = catalog.db.execute(
                "SELECT id,name FROM authors WHERE name LIKE ? ORDER BY name LIMIT 20", (f"%{name}%",)
            ).fetchall()

        entries = []
        seen = set()
        for author in authors:
            aid = str(author["id"])
            works = catalog.db.execute(
                "SELECT id,title,subjects,categories FROM works WHERE authors LIKE ? ORDER BY title LIMIT ?",
                (f'%"{aid}"%', limit),
            ).fetchall()
            for work in works:
                wid_raw = str(work["id"])
                if wid_raw in seen:
                    continue
                seen.add(wid_raw)
                editions = catalog.db.execute(
                    "SELECT id,publish_date,publishers,language FROM editions WHERE work_id=? ORDER BY publish_date LIMIT 12",
                    (wid_raw,),
                ).fetchall()
                years = [y for y in (_year(e["publish_date"]) for e in editions) if y is not None]
                pubs = []
                languages = []
                edition_items = []
                for edition in editions:
                    p = _items(edition["publishers"])
                    pubs.extend(p)
                    if edition["language"]:
                        languages.append(str(edition["language"]))
                    edition_items.append({
                        "edition_id": _eid(str(edition["id"])),
                        "publish_date": edition["publish_date"],
                        "publishers": p,
                        "language": edition["language"],
                    })
                entries.append({
                    "author_id": aid,
                    "author": str(author["name"]),
                    "work_id": _wid(wid_raw),
                    "title": str(work["title"]),
                    "year": min(years) if years else None,
                    "subjects": normalize_subjects(_items(work["subjects"]), 128),
                    "categories": _items(work["categories"]),
                    "publishers": list(dict.fromkeys(pubs)),
                    "languages": list(dict.fromkeys(languages)),
                    "editions": edition_items,
                })
                if len(entries) >= limit:
                    break
            if len(entries) >= limit:
                break

    entries.sort(key=lambda x: (x["year"] is None, x["year"] or 9999, x["title"].casefold()))
    return {
        "kind": "author_timeline",
        "query": name,
        "authors": [{"id": str(a["id"]), "name": str(a["name"])} for a in authors],
        "entries": entries,
    }


def publisher_map(catalog: CatalogDB, name: str, limit: int = 150) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("publisher name is required")
    limit = max(1, min(int(limit), 500))
    needle = name.casefold()
    with catalog._lock:
        rows = catalog.db.execute(
            "SELECT e.id,e.work_id,e.title,e.publishers,e.publish_date,e.language,w.title work_title,w.categories,w.subjects "
            "FROM editions e LEFT JOIN works w ON w.id=e.work_id WHERE e.publishers LIKE ? ORDER BY e.publish_date LIMIT ?",
            (f"%{name}%", limit * 4),
        ).fetchall()

    editions = []
    category_counts: Counter[str] = Counter()
    subject_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    publisher_counts: Counter[str] = Counter()
    for row in rows:
        publishers = _items(row["publishers"])
        if not any(needle in p.casefold() for p in publishers):
            continue
        categories = _items(row["categories"])
        subjects = normalize_subjects(_items(row["subjects"]), 128)
        year = _year(row["publish_date"])
        for value in categories: category_counts[value] += 1
        for value in subjects[:12]: subject_counts[value] += 1
        for value in publishers: publisher_counts[value] += 1
        if year is not None: year_counts[str(year)] += 1
        if row["language"]: language_counts[str(row["language"])] += 1
        editions.append({
            "edition_id": _eid(str(row["id"])),
            "work_id": _wid(str(row["work_id"])) if row["work_id"] else None,
            "title": str(row["work_title"] or row["title"] or ""),
            "publishers": publishers,
            "publish_date": row["publish_date"],
            "language": row["language"],
            "categories": categories,
        })
        if len(editions) >= limit:
            break

    canonical = publisher_counts.most_common(1)[0][0] if publisher_counts else name
    root = f"publisher:{canonical.casefold()}"
    nodes = [{"id": root, "kind": "publisher", "label": canonical, "weight": len(editions)}]
    edges = []
    for category, count in category_counts.most_common(16):
        cid = f"category:{category.casefold()}"
        nodes.append({"id": cid, "kind": "category", "label": category, "weight": count})
        edges.append({"source": root, "target": cid, "kind": "publishes-category", "weight": count})
    return {
        "kind": "publisher_map",
        "query": name,
        "publisher": canonical,
        "nodes": nodes,
        "edges": edges,
        "editions": editions,
        "top_subjects": [{"name": key, "count": count} for key, count in subject_counts.most_common(24)],
        "years": [{"year": key, "count": year_counts[key]} for key in sorted(year_counts)],
        "languages": [{"language": key, "count": count} for key, count in language_counts.most_common()],
    }
