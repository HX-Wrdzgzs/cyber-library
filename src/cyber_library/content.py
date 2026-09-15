from __future__ import annotations

import hashlib
import html
import re
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

RIGHTS_VALUES = {"public-domain", "open-license", "licensed", "user-provided"}

class ContentError(RuntimeError):
    pass

@dataclass(slots=True)
class ContentDocument:
    title: str
    text: str
    headings: list[str]
    content_hash: str
    source_path: str
    rights: str

class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True); self.parts=[]; self.headings=[]; self._skip=0; self._heading_tag=None; self._heading_parts=[]
    def handle_starttag(self, tag, attrs) -> None:
        tag=tag.lower()
        if tag in {"script","style","svg","noscript"}: self._skip+=1
        if tag in {"h1","h2","h3","h4","h5","h6"} and self._skip==0: self._heading_tag=tag; self._heading_parts=[]
        if tag in {"p","div","br","li","section","article"} and self._skip==0: self.parts.append("\n")
    def handle_endtag(self, tag) -> None:
        tag=tag.lower()
        if tag in {"script","style","svg","noscript"} and self._skip: self._skip-=1
        if self._heading_tag==tag:
            heading=re.sub(r"\s+"," ","".join(self._heading_parts)).strip()
            if heading and heading not in self.headings: self.headings.append(heading)
            self._heading_tag=None; self._heading_parts=[]; self.parts.append("\n")
    def handle_data(self,data) -> None:
        if self._skip:return
        self.parts.append(data)
        if self._heading_tag:self._heading_parts.append(data)
    def result(self):
        text=html.unescape("".join(self.parts)); text=re.sub(r"[ \t]+"," ",text); text=re.sub(r"\n\s*\n+","\n\n",text); return text.strip(),self.headings

def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

def _plain_text(path: Path):
    raw=path.read_bytes()
    for encoding in ("utf-8-sig","utf-16","gb18030","big5","latin-1"):
        try: text=raw.decode(encoding); break
        except UnicodeDecodeError: continue
    else: raise ContentError(f"Could not decode text file: {path}")
    headings=[]
    for line in text.splitlines():
        stripped=line.strip()
        if re.match(r"^#{1,6}\s+\S",stripped): headings.append(re.sub(r"^#{1,6}\s+","",stripped))
        elif re.match(r"^(chapter|part)\s+\w+",stripped,flags=re.I): headings.append(stripped)
        elif re.match(r"^第[一二三四五六七八九十百千万零〇\d]+[章节卷部篇]",stripped): headings.append(stripped)
    return text.strip(),list(dict.fromkeys(headings))[:500]

def _epub_order(zf: zipfile.ZipFile):
    try:
        container=ElementTree.fromstring(zf.read("META-INF/container.xml")); rootfile=container.find(".//{*}rootfile")
        if rootfile is None: raise ValueError
        opf_path=rootfile.attrib["full-path"]; opf=ElementTree.fromstring(zf.read(opf_path)); base=Path(opf_path).parent; manifest={}
        for item in opf.findall(".//{*}manifest/{*}item"):
            item_id=item.attrib.get("id"); href=item.attrib.get("href")
            if item_id and href: manifest[item_id]=str((base/href).as_posix())
        ordered=[]
        for itemref in opf.findall(".//{*}spine/{*}itemref"):
            target=manifest.get(itemref.attrib.get("idref",""))
            if target: ordered.append(target)
        if ordered:return ordered
    except Exception: pass
    return sorted(name for name in zf.namelist() if name.lower().endswith((".xhtml",".html",".htm")) and not name.lower().endswith(("nav.xhtml","toc.html")))

def _epub_text(path: Path):
    if not zipfile.is_zipfile(path): raise ContentError("EPUB is not a valid ZIP container")
    texts=[]; headings=[]
    with zipfile.ZipFile(path) as zf:
        for name in _epub_order(zf):
            try: raw=zf.read(name).decode("utf-8","replace")
            except KeyError: continue
            parser=_HTMLTextExtractor(); parser.feed(raw); text,file_headings=parser.result()
            if text:texts.append(text)
            headings.extend(file_headings)
    text="\n\n".join(texts).strip()
    if not text: raise ContentError("No readable XHTML text was found in EPUB")
    return text,list(dict.fromkeys(headings))[:500]

def _pdf_text(path: Path):
    try: from pypdf import PdfReader
    except ImportError as exc: raise ContentError("PDF extraction is optional. Install with: pip install 'cyber-library[pdf]'") from exc
    text="\n\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages).strip()
    if not text: raise ContentError("PDF contained no extractable text")
    return text,[]

def extract_document(path: str | Path, rights: str, title: str | None = None) -> ContentDocument:
    path=Path(path)
    if rights not in RIGHTS_VALUES: raise ContentError("rights must be one of: "+", ".join(sorted(RIGHTS_VALUES)))
    if not path.is_file(): raise ContentError(f"File not found: {path}")
    suffix=path.suffix.lower()
    if suffix in {".txt",".md",".markdown"}: text,headings=_plain_text(path)
    elif suffix==".epub": text,headings=_epub_text(path)
    elif suffix==".pdf": text,headings=_pdf_text(path)
    else: raise ContentError("Supported input formats: .txt, .md, .epub, .pdf")
    if len(text)<100: raise ContentError("Extracted text is too short for full-text analysis")
    return ContentDocument(title=title or path.stem,text=text,headings=headings,content_hash=_hash(text),source_path=str(path),rights=rights)
