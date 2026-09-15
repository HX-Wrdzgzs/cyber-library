# Cyber Library

> **在出版知识中航行。**  
> An evidence-aware catalog, knowledge graph, analysis engine and visual ISBN universe.

Cyber Library 的目标不是“把世界上所有 PDF 放在一起”，而是建立一个可扩展的出版知识基础设施：

- 把 **Work（作品）** 与 **Edition（版本）** 分开；
- 用 ISBN、Open Library ID、OCLC、LCCN 等标识符连接版本；
- 从公开书目元数据构建分类、标签、搜索和知识关系；
- 在来源证据足够时生成目录、大纲、概述、详细解读、章节摘要与思维导图；
- 对用户有权分析的 TXT / Markdown / EPUB / PDF 做全文分析；
- 把带 ISBN 的版本映射到一个可缩放的二维 **ISBN Universe**；
- 大规模数据走 Open Library 月度 dump，实时 API 只做低频的人触发查询。

项目当前版本：**v1.0.0**

## What works now

```text
Open Library dump / low-volume API / local content
                    │
                    ▼
          ┌──────────────────┐
          │ Normalized Catalog│
          │ Work / Edition    │
          └────────┬─────────┘
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
    Search     Intelligence    Graph
  SQLite FTS   evidence-aware  relations
       │           │            │
       └───────────┼────────────┘
                   ▼
             Web Explorer
          ISBN Universe + API
```

已实现：

- ISBN-10 / ISBN-13 校验、统一和坐标映射；
- Open Library Work / Edition / Author 导入；
- SQLite 本地目录；
- FTS5 搜索（不可用时自动退回 SQL 搜索）；
- 20 个顶层知识分类 + 原始 Subjects / Tags；
- Open Library 简介、目录、首句、notes、excerpts 证据抽取；
- 目录级分析、来源级分析、全文级分析；
- 可选 OpenAI-compatible LLM 增强；
- 没有 LLM 时仍可本地运行确定性摘要/关键词/章节结构分析；
- 本地 TXT / Markdown / EPUB 解析；
- 可选 PDF 提取；
- 思维导图 JSON；
- 作品 / 作者 / Subject / 分类 / 出版社 / 年份 / 相关作品知识图谱；
- 独立实现的 Hilbert ISBN Space；
- Web 搜索、详情、全文分析、知识图谱、ISBN 宇宙；
- REST API；
- Docker / Compose；
- Python 3.11–3.13 CI。

## Quick start

```bash
git clone https://github.com/HX-Wrdzgzs/cyber-library.git
cd cyber-library
python -m pip install -e .
```

验证：

```bash
cyber-library isbn 0-306-40615-2
cyber-library space 9780306406157
cyber-library categories
```

低频实时解析：

```bash
export CYBER_LIBRARY_CONTACT="you@example.com"

cyber-library resolve 9780140328721 \
  --analysis auto
```

启动 Web：

```bash
cyber-library serve \
  --host 0.0.0.0 \
  --port 8080 \
  --contact you@example.com
```

打开 `http://localhost:8080`。

## Build a local catalog

Open Library 明确建议：批量项目使用月度 dumps，而不是扫 API。

下载官方 dump 后，可以一次导入多个文件：

```bash
cyber-library import-dump \
  ol_dump_authors_latest.txt.gz \
  ol_dump_works_latest.txt.gz \
  ol_dump_editions_latest.txt.gz \
  --db data/catalog.sqlite3
```

导入结束后默认重建：

- 搜索索引；
- ISBN Universe 坐标。

如果是超大导入，希望把重建索引放到最后：

```bash
cyber-library import-dump ol_dump_editions_latest.txt.gz \
  --db data/catalog.sqlite3 \
  --skip-reindex

cyber-library reindex --db data/catalog.sqlite3
```

使用本地目录启动：

```bash
cyber-library serve \
  --db data/catalog.sqlite3 \
  --contact you@example.com
```

## Search

```bash
cyber-library search "machine learning" \
  --db data/catalog.sqlite3 \
  --category "Computer Science" \
  --limit 20
```

本地搜索优先。如果本地没有结果且未指定 `--no-live`，会低频回退到 Open Library Search API。

## Book intelligence

Cyber Library 不把“模型说出来的话”直接当书目事实。

分析分为四个证据层级：

| Level | Evidence | Output |
|---|---|---|
| L0 | 纯书目事实 | 不做内容解释 |
| L1 | title / author / subjects / publisher | 概览、分类、Tags |
| L2 | description / TOC / notes / excerpts | 来源约束的总结、详细解读、结构 |
| L3 | 有权分析的完整正文 | 全文摘要、章节摘要、大纲、主题、思维导图 |

`auto` 会自动选择当前证据支持的最高层级。

```bash
cyber-library resolve 9780140328721 --analysis auto
```

### Optional LLM enhancement

没有 LLM 也能工作。配置一个 OpenAI-compatible `/chat/completions` endpoint 后，会在严格的来源边界内增强结构化分析：

```bash
export CYBER_LIBRARY_LLM_BASE_URL="http://127.0.0.1:8000/v1"
export CYBER_LIBRARY_LLM_MODEL="your-model"
export CYBER_LIBRARY_LLM_API_KEY=""
```

关闭：

```bash
cyber-library resolve 9780140328721 --analysis auto --no-llm
```

Cyber Library 不要求某一家模型提供商。

## Full-text analysis

仅用于你有权分析的内容。

支持：

- `.txt`
- `.md` / `.markdown`
- `.epub`
- `.pdf`（安装 `cyber-library[pdf]`）

```bash
cyber-library analyze-file book.epub \
  --rights user-provided \
  --title "My Book"
```

合法权限声明：

```text
public-domain
open-license
licensed
user-provided
```

如果知道 ISBN：

```bash
cyber-library analyze-file book.txt \
  --rights licensed \
  --isbn 9780306406157
```

默认不会把全文保存进数据库；数据库只记录分析结果、内容哈希、来源路径和权限声明。

## ISBN Universe

`isbn-visualization` 给了这个项目最初的视觉灵感，但 Cyber Library **没有复制其源码**。

本项目使用独立实现的坐标系统：

```text
ISBN-13 前 12 位
       │
978/979 namespace offset
       │
scaled Hilbert distance
       │
65,536 × 65,536 coordinate plane
```

因此主项目继续使用 MIT License，不把上游 AGPL 代码混入本仓库。

Web 的“ISBN 宇宙”页面支持：

- 浏览本地目录坐标；
- 分类过滤；
- 搜索高亮；
- 滚轮缩放；
- 拖动平移；
- 点击图书打开详情。

详见 [`docs/universe.md`](docs/universe.md)。

## API

主要接口：

```text
GET  /api/health
GET  /api/stats
GET  /api/categories
GET  /api/resolve?isbn=...&analysis=auto
GET  /api/search?q=...&category=...
GET  /api/graph?isbn=...
GET  /api/universe?min_x=...&max_x=...
POST /api/analyze-text
```

完整说明：[`docs/api.md`](docs/api.md)。

## Docker

```bash
docker compose up --build
```

默认挂载：

```text
./data              -> /app/data
./.cyber-library    -> /app/.cyber-library
```

访问 `http://localhost:8080`。

## Data model

```text
Author ────────┐
               ▼
              Work
        ┌──────┼──────┐
        ▼      ▼      ▼
     Edition Edition Edition
        │
        ├─ ISBN-13
        ├─ ISBN-10
        ├─ OCLC
        ├─ LCCN
        └─ Internet Archive ID

Work / Edition
      │
      ├─ Provenance
      ├─ Evidence
      ├─ Analysis
      └─ Knowledge Graph
```

核心原则：

> `Book != ISBN`

ISBN 标识某个出版版本，不等于抽象作品本身。

## Data sources and limits

当前原生适配器重点是 Open Library：

- 大规模：月度 dumps；
- 低频实时：Work / Edition / Author / Search APIs；
- 封面：Open Library Covers API。

Open Library 本身也不等于“世界上所有书”。没有 ISBN 的古籍、手稿、灰色文献、部分自出版物等需要以后通过额外标识符和来源进入同一 Work/Edition 模型。

详见 [`docs/data-sources.md`](docs/data-sources.md)。

## Copyright / rights boundary

本项目是目录、知识索引和分析框架，不是影子图书馆。

它不会提供绕过借阅、DRM、付费墙或访问控制的功能。书目元数据、封面、软件源码和书籍正文是不同的权利对象，必须分别处理。

全文分析入口要求调用方声明合法分析依据，并默认不持久化原文。

## Repository layout

```text
src/cyber_library/
├─ cache.py
├─ cli.py
├─ content.py
├─ database.py
├─ dump.py
├─ evidence.py
├─ graph.py
├─ identifiers.py
├─ intelligence.py
├─ llm.py
├─ models.py
├─ server.py
├─ service.py
├─ taxonomy.py
├─ universe.py
└─ sources/
   └─ openlibrary.py

web/
tests/
schemas/
docs/
```

## Related project

Visual inspiration / reference:

- [`phiresky/isbn-visualization`](https://github.com/phiresky/isbn-visualization)

See [`references/isbn-visualization.md`](references/isbn-visualization.md).

## License

Cyber Library original source code is licensed under the MIT License.

Third-party datasets, covers, book content and external projects retain their own rights and terms.
