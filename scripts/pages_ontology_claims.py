#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add a static Ontology Lite + evidence-bounded Claim Graph to GitHub Pages.

This is a read-only derived layer. Existing WeRead exports remain the source of
truth. No API, model, backend, or browser network request is required.

Public contract:
- entities/relations are metadata and aggregate counts only;
- raw mark/review bodies are never embedded here;
- claims are deterministic observations with support/counter/dependency fields;
- uncertainty stays explicit via supported / partial / unresolved.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "site"


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def bid(row: dict) -> str:
    return str(row.get("bookId") or (row.get("book") or {}).get("bookId") or "")


def title_of(row: dict) -> str:
    book = row.get("book") or row
    return str(book.get("title") or row.get("title") or "未命名").strip() or "未命名"


def author_of(row: dict) -> str:
    book = row.get("book") or row
    return str(book.get("author") or row.get("author") or "未知").strip() or "未知"


def category_of(row: dict) -> str:
    book = row.get("book") or row
    direct = str(book.get("category") or row.get("category") or "").strip()
    if direct:
        return direct
    for item in book.get("categories") or []:
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            value = item.get("title") or item.get("category") or item.get("name")
            if value:
                return str(value).strip()
    return "未知"


def parse_time(raw):
    try:
        value = int(float(raw or 0))
        if value > 10_000_000_000:
            value //= 1000
        if value <= 0:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def relation_id(prefix: str, text: str) -> str:
    return f"{prefix}:{sha1(text.encode('utf-8')).hexdigest()[:12]}"


def progress_value(progress: dict, book_id: str):
    row = progress.get(book_id) or {}
    value = row.get("progress")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_payload(data_dir: Path = DATA, *, include_private: bool = True) -> dict:
    shelf = load_json(data_dir / "weread_shelf.json", {})
    notebooks = load_json(data_dir / "weread_notebooks.json", [])
    notes = load_json(data_dir / "weread_notes_export.json", [])
    progress = load_json(data_dir / "weread_progress.json", {})

    shelf_rows = list((shelf or {}).get("books") or [])
    secret_ids = {bid(x) for x in shelf_rows if bid(x) and int(x.get("secret") or 0) == 1}
    if not include_private:
        shelf_rows = [x for x in shelf_rows if bid(x) not in secret_ids]
        notebooks = [x for x in notebooks if bid(x) not in secret_ids]
        notes = [x for x in notes if bid(x) not in secret_ids]

    shelf_by = {bid(x): x for x in shelf_rows if bid(x)}
    notebook_by = {bid(x): x for x in notebooks if bid(x)}
    notes_by = {bid(x): x for x in notes if bid(x)}
    all_ids = sorted(set(shelf_by) | set(notebook_by) | set(notes_by))

    authors: set[str] = set()
    categories: set[str] = set()
    chapters: set[tuple[str, str]] = set()
    evidence_count = 0
    marks_count = 0
    reviews_count = 0
    evidence_with_chapter = 0
    book_rows = []
    author_cat_evidence: dict[str, Counter] = defaultdict(Counter)
    yearly_category: dict[str, Counter] = defaultdict(Counter)

    for book_id in all_ids:
        source = shelf_by.get(book_id) or notebook_by.get(book_id) or notes_by.get(book_id) or {}
        note_row = notes_by.get(book_id) or {}
        title = title_of(source)
        author = author_of(source)
        category = category_of(source)
        if category == "未知":
            category = category_of(notebook_by.get(book_id) or {})
        if author == "未知":
            author = author_of(notebook_by.get(book_id) or {})
        if author != "未知":
            authors.add(author)
        if category != "未知":
            categories.add(category)

        chapter_counts = Counter()
        times = []
        marks = list(note_row.get("marks") or [])
        reviews = list(note_row.get("reviews") or [])
        marks_count += len(marks)
        reviews_count += len(reviews)
        total = len(marks) + len(reviews)
        evidence_count += total
        if author != "未知" and category != "未知" and total:
            author_cat_evidence[author][category] += total

        for kind, rows in (("mark", marks), ("review", reviews)):
            for item in rows:
                if not isinstance(item, dict):
                    continue
                chapter = str(item.get("chapter") or "").strip()
                if chapter:
                    chapters.add((book_id, chapter))
                    chapter_counts[chapter] += 1
                    evidence_with_chapter += 1
                when = parse_time(item.get("createTime"))
                if when:
                    times.append(when)
                    if category != "未知":
                        yearly_category[str(when.year)][category] += 1

        sorted_chapters = chapter_counts.most_common()
        book_rows.append({
            "bookId": book_id,
            "title": title,
            "author": author,
            "category": category,
            "evidence": total,
            "marks": len(marks),
            "reviews": len(reviews),
            "progress": progress_value(progress, book_id),
            "chapterCount": len(chapter_counts),
            "topChapters": [{"chapter": c, "evidence": n} for c, n in sorted_chapters[:4]],
            "topChapterShare": round(100 * sorted_chapters[0][1] / total, 1) if sorted_chapters and total else 0.0,
            "firstEvidence": min(times).date().isoformat() if times else None,
            "lastEvidence": max(times).date().isoformat() if times else None,
            "spanDays": (max(times).date() - min(times).date()).days if len(times) >= 2 else 0,
        })

    relation_counts = {
        "writtenBy": sum(1 for b in book_rows if b["author"] != "未知"),
        "belongsTo": sum(1 for b in book_rows if b["category"] != "未知"),
        "contains": len(chapters),
        "evidenceFromBook": evidence_count,
        "evidenceFromChapter": evidence_with_chapter,
    }
    entity_counts = {
        "Book": len(book_rows),
        "Author": len(authors),
        "Category": len(categories),
        "Chapter": len(chapters),
        "Evidence": evidence_count,
    }

    # Focused ontology graph: top evidence books plus their category/author/top chapters.
    focus_books = sorted((b for b in book_rows if b["evidence"] > 0), key=lambda x: (-x["evidence"], x["title"]))[:7]
    nodes = []
    edges = []
    seen = set()

    def add_node(node_id: str, label: str, kind: str, value: int | float = 0):
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append({"id": node_id, "label": label, "kind": kind, "value": value})

    for book in focus_books:
        bnode = f"book:{book['bookId']}"
        add_node(bnode, book["title"], "book", book["evidence"])
        if book["category"] != "未知":
            cnode = relation_id("category", book["category"])
            add_node(cnode, book["category"], "category", 0)
            edges.append({"source": cnode, "target": bnode, "relation": "belongsTo", "value": book["evidence"]})
        if book["author"] != "未知":
            anode = relation_id("author", book["author"])
            add_node(anode, book["author"], "author", 0)
            edges.append({"source": bnode, "target": anode, "relation": "writtenBy", "value": book["evidence"]})
        for row in book["topChapters"][:3]:
            hnode = relation_id("chapter", book["bookId"] + "\0" + row["chapter"])
            add_node(hnode, row["chapter"], "chapter", row["evidence"])
            edges.append({"source": bnode, "target": hnode, "relation": "contains", "value": row["evidence"]})

    claims = []

    # 1) Bridge-author claims: direct relationship evidence, qualified if one category dominates.
    bridge_rows = []
    for author, counts in author_cat_evidence.items():
        if len(counts) < 2:
            continue
        total = sum(counts.values())
        top_cat, top_n = counts.most_common(1)[0]
        dominance = round(100 * top_n / total, 1) if total else 0.0
        bridge_rows.append((len(counts), total, author, counts, top_cat, dominance))
    bridge_rows.sort(key=lambda x: (-x[0], -x[1], x[2]))
    for category_count, total, author, counts, top_cat, dominance in bridge_rows[:4]:
        counter = []
        status = "supported"
        if dominance >= 80:
            counter.append({"label": "分布限定", "value": f"{top_cat} 占该作者证据 {dominance}%"})
            status = "partial"
        claims.append({
            "id": relation_id("claim", "bridge:" + author),
            "type": "bridge-author",
            "title": "跨类别桥接",
            "statement": f"{author} 的阅读证据跨越 {category_count} 个类别。",
            "status": status,
            "support": [
                {"label": "类别", "value": " / ".join(counts.keys())},
                {"label": "证据量", "value": f"{total:,} 条"},
            ],
            "counter": counter,
            "dependencies": ["类别来自当前书目元数据", "证据量 = 划线 + 本人想法计数"],
        })

    # 2) Year-over-year category share changes. Share and absolute count are separated.
    years = sorted(yearly_category)
    for previous_year, year in zip(years, years[1:]):
        prev = yearly_category[previous_year]
        cur = yearly_category[year]
        prev_total, cur_total = sum(prev.values()), sum(cur.values())
        if not prev_total or not cur_total:
            continue
        deltas = []
        for category in set(prev) | set(cur):
            prev_share = prev.get(category, 0) / prev_total
            cur_share = cur.get(category, 0) / cur_total
            deltas.append((cur_share - prev_share, category, prev.get(category, 0), cur.get(category, 0), prev_share, cur_share))
        candidates = [x for x in sorted(deltas, reverse=True) if x[0] >= .05]
        if not candidates:
            continue
        delta, category, prev_n, cur_n, prev_share, cur_share = candidates[0]
        counter = []
        status = "supported"
        if cur_n <= prev_n:
            counter.append({"label": "绝对量限定", "value": f"占比上升，但笔记数 {prev_n} → {cur_n}"})
            status = "partial"
        claims.append({
            "id": relation_id("claim", f"shift:{previous_year}:{year}:{category}"),
            "type": "focus-shift",
            "title": "年度关注占比变化",
            "statement": f"{year} 年 {category} 的笔记占比较 {previous_year} 年上升 {delta*100:.1f}pp。",
            "status": status,
            "support": [
                {"label": previous_year, "value": f"{prev_n} 条 · {prev_share*100:.1f}%"},
                {"label": year, "value": f"{cur_n} 条 · {cur_share*100:.1f}%"},
            ],
            "counter": counter,
            "dependencies": ["只描述笔记结构变化，不推断兴趣变化原因"],
        })

    # 3) Cross-chapter evidence claims. Concentration is surfaced as a qualifier.
    chapter_books = sorted(
        (b for b in book_rows if b["evidence"] >= 12 and b["chapterCount"] >= 3),
        key=lambda x: (-x["evidence"], -x["chapterCount"], x["title"]),
    )
    for book in chapter_books[:4]:
        counter = []
        status = "supported"
        if book["topChapterShare"] >= 60:
            top = book["topChapters"][0]
            counter.append({"label": "集中度限定", "value": f"“{top['chapter']}”占全部证据 {book['topChapterShare']}%"})
            status = "partial"
        claims.append({
            "id": relation_id("claim", "chapters:" + book["bookId"]),
            "type": "chapter-evidence",
            "title": "跨章节证据",
            "statement": f"《{book['title']}》的证据分布在 {book['chapterCount']} 个章节。",
            "status": status,
            "support": [
                {"label": "证据量", "value": f"{book['evidence']:,} 条"},
                {"label": "高频章节", "value": " / ".join(f"{x['chapter']}({x['evidence']})" for x in book["topChapters"][:3])},
            ],
            "counter": counter,
            "dependencies": ["章节名来自个人笔记导出", "不使用划线/想法正文进行语义推断"],
        })

    # 4) Long-span evidence: a direct temporal observation.
    spans = sorted((b for b in book_rows if b["spanDays"] >= 180 and b["evidence"] > 0), key=lambda x: (-x["spanDays"], -x["evidence"]))
    for book in spans[:2]:
        claims.append({
            "id": relation_id("claim", "span:" + book["bookId"]),
            "type": "evidence-span",
            "title": "长期回访证据",
            "statement": f"《{book['title']}》的证据记录跨越 {book['spanDays']} 天。",
            "status": "supported",
            "support": [
                {"label": "首条证据", "value": book["firstEvidence"] or "—"},
                {"label": "末条证据", "value": book["lastEvidence"] or "—"},
                {"label": "证据量", "value": f"{book['evidence']:,} 条"},
            ],
            "counter": [],
            "dependencies": ["时间跨度只表示证据出现跨度，不等于持续每天阅读"],
        })

    # 5) Explicit unresolved state when a high-evidence book lacks progress data.
    unknown = next((b for b in sorted(book_rows, key=lambda x: -x["evidence"]) if b["evidence"] >= 20 and b["progress"] is None), None)
    if unknown:
        claims.append({
            "id": relation_id("claim", "progress-unknown:" + unknown["bookId"]),
            "type": "unresolved",
            "title": "完成状态待确认",
            "statement": f"无法仅凭现有数据判断《{unknown['title']}》的高证据量是否对应读完。",
            "status": "unresolved",
            "support": [{"label": "已有证据", "value": f"{unknown['evidence']:,} 条"}],
            "counter": [{"label": "缺失字段", "value": "当前缓存没有可靠阅读进度"}],
            "dependencies": ["需要有效 progress 数据后才能判断完成状态"],
        })

    status_counts = Counter(x["status"] for x in claims)
    return {
        "version": "1.0",
        "contract": {
            "derivedReadOnly": True,
            "deterministicClaims": True,
            "rawTextPublished": False,
            "runtimeApiRequired": False,
            "sourceOfTruth": "existing WeRead exports",
        },
        "ontology": {
            "entityCounts": entity_counts,
            "relationCounts": relation_counts,
            "graph": {"nodes": nodes, "edges": edges},
            "focusBookCount": len(focus_books),
        },
        "claimGraph": {
            "count": len(claims),
            "statusCounts": dict(status_counts),
            "claims": claims,
        },
    }


CSS = r'''
.ontology-stat-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}.ontology-stat{border:1px solid var(--line);border-radius:16px;padding:13px;min-width:0}.ontology-stat span{display:block;color:var(--muted);font-size:10px}.ontology-stat b{display:block;margin-top:5px;font-size:20px}.ontology-contract{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 16px}.ontology-contract span{border:1px solid var(--line);border-radius:999px;padding:5px 8px;font-size:10px;color:var(--muted)}.ontology-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:18px;padding:8px}.ontology-svg{display:block;width:100%;min-width:980px;height:auto}.og-edge{stroke:color-mix(in srgb,var(--muted) 34%,transparent);fill:none}.og-label{fill:var(--ink);font-size:10px}.og-head{fill:var(--muted);font-size:9px;letter-spacing:.08em}.og-category{fill:var(--accent2)}.og-book{fill:var(--accent3)}.og-chapter{fill:color-mix(in srgb,var(--accent2) 58%,var(--accent3))}.og-author{fill:var(--accent)}.relation-strip{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.relation-chip{border:1px solid var(--line);border-radius:999px;padding:5px 8px;font-size:10px}.relation-chip b{margin-left:4px}.claim-toolbar{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}.claim-filter{border:1px solid var(--line);background:var(--paper);color:var(--muted);border-radius:999px;padding:6px 10px;cursor:pointer;font:inherit;font-size:11px}.claim-filter.active{background:var(--ink);color:var(--paper);border-color:var(--ink)}.claim-layout{display:grid;grid-template-columns:minmax(260px,.82fr) minmax(0,1.18fr);gap:14px}.claim-list{display:grid;gap:8px;align-content:start;max-height:560px;overflow:auto;padding-right:3px}.claim-row{width:100%;text-align:left;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:14px;padding:11px 12px;cursor:pointer}.claim-row.active{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}.claim-row-top{display:flex;align-items:center;justify-content:space-between;gap:8px}.claim-row small{display:block;color:var(--muted);margin-top:5px;line-height:1.45}.claim-status{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:3px 6px;font-size:9px;white-space:nowrap}.claim-status.supported{color:var(--accent2)}.claim-status.partial{color:var(--accent)}.claim-status.unresolved{color:var(--muted)}.claim-detail{border:1px solid var(--line);border-radius:18px;padding:16px;min-height:330px}.claim-detail h3{margin:4px 0 8px;font-size:18px}.claim-detail-kicker{font-size:10px;color:var(--accent);letter-spacing:.1em;text-transform:uppercase}.claim-node{border:1px solid var(--line);border-radius:16px;padding:13px;background:color-mix(in srgb,var(--paper) 94%,var(--bg));margin:12px 0}.claim-evidence-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.claim-evidence-box{border-top:1px solid var(--line);padding-top:10px}.claim-evidence-box h4{font-size:11px;margin:0 0 8px;color:var(--muted)}.claim-evidence-item{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid color-mix(in srgb,var(--line) 65%,transparent);font-size:11px}.claim-evidence-item span:first-child{color:var(--muted)}.claim-deps{margin:12px 0 0;padding-left:18px;color:var(--muted);font-size:10px}.claim-empty{color:var(--muted);font-size:11px}.claim-legend{font-size:11px;color:var(--muted);margin:0 0 14px}.claim-legend b{color:var(--ink)}
@media(max-width:900px){.ontology-stat-grid{grid-template-columns:repeat(3,1fr)}.claim-layout{grid-template-columns:1fr}.claim-list{max-height:none;grid-template-columns:1fr 1fr}.claim-detail{min-height:0}}@media(max-width:560px){.ontology-stat-grid{grid-template-columns:1fr 1fr}.claim-list{grid-template-columns:1fr}.claim-evidence-grid{grid-template-columns:1fr}}
'''

HTML = r'''
  <article class="card wide" id="ontology-lite"><div class="title"><div><div class="section-kicker">Ontology Lite</div><h2>阅读本体 · 只读关系层</h2></div><small>由现有 WeRead 数据构建；不新增第二套可写真相源</small></div><div class="ontology-contract"><span>Book</span><span>Author</span><span>Category</span><span>Chapter</span><span>Evidence</span><span>构建时派生</span><span>无运行时 API</span></div><div class="ontology-stat-grid" id="ontologyStats"></div><div class="ontology-wrap"><svg class="ontology-svg" id="ontologyGraph" viewBox="0 0 1120 560" role="img" aria-label="阅读本体关系图"></svg></div><div class="relation-strip" id="ontologyRelations"></div></article>
  <article class="card wide" id="claim-graph"><div class="title"><div><div class="section-kicker">Evidence Claim Graph</div><h2>证据主张图</h2></div><small>claim → support / qualifier / dependency；不知道就保留不知道</small></div><p class="claim-legend"><b>已支持</b> = 当前数据直接支持；<b>有限定</b> = 主张成立但有需要同时看的反向/限定证据；<b>待确认</b> = 缺字段时不补猜测。</p><div class="claim-toolbar" id="claimToolbar"></div><div class="claim-layout"><div class="claim-list" id="claimList"></div><div class="claim-detail" id="claimDetail"></div></div></article>
'''

JS_TEMPLATE = r'''
(()=>{
const OCG=__PAYLOAD__;
const escO=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const counts=OCG.ontology?.entityCounts||{},relations=OCG.ontology?.relationCounts||{};
const entityOrder=[['Book','书'],['Author','作者'],['Category','类别'],['Chapter','章节'],['Evidence','证据']];
const stat=document.getElementById('ontologyStats');if(stat)stat.innerHTML=entityOrder.map(([k,l])=>`<div class="ontology-stat"><span>${l} · ${k}</span><b>${(+counts[k]||0).toLocaleString()}</b></div>`).join('');
const relationNames={writtenBy:'书 → 作者',belongsTo:'书 → 类别',contains:'书 → 章节',evidenceFromBook:'证据 → 书',evidenceFromChapter:'证据 → 章节'};
const strip=document.getElementById('ontologyRelations');if(strip)strip.innerHTML=Object.entries(relationNames).map(([k,l])=>`<span class="relation-chip">${l}<b>${(+relations[k]||0).toLocaleString()}</b></span>`).join('');
function drawOntology(){const svg=document.getElementById('ontologyGraph'),G=OCG.ontology?.graph||{},nodes=G.nodes||[],edges=G.edges||[];if(!svg)return;if(!nodes.length){svg.innerHTML='<text x="30" y="50" class="og-label">暂无关系数据</text>';return}const groups={category:nodes.filter(n=>n.kind==='category'),book:nodes.filter(n=>n.kind==='book'),chapter:nodes.filter(n=>n.kind==='chapter'),author:nodes.filter(n=>n.kind==='author')},xs={category:100,book:390,chapter:760,author:1040},pos={};Object.entries(groups).forEach(([kind,rows])=>{const step=470/Math.max(1,rows.length);rows.forEach((n,i)=>pos[n.id]=[xs[kind],55+step*(i+.5)])});let out='<text x="70" y="24" class="og-head">CATEGORY</text><text x="365" y="24" class="og-head">BOOK</text><text x="735" y="24" class="og-head">CHAPTER</text><text x="1010" y="24" class="og-head">AUTHOR</text>';const max=Math.max(1,...edges.map(e=>+e.value||0));edges.forEach(e=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return;const w=.6+4*(+e.value||0)/max;out+=`<path class="og-edge" stroke-width="${w.toFixed(2)}" d="M${a[0]},${a[1]} C${(a[0]+b[0])/2},${a[1]} ${(a[0]+b[0])/2},${b[1]} ${b[0]},${b[1]}"><title>${escO(e.relation)} · ${e.value}</title></path>`});nodes.forEach(n=>{const p=pos[n.id];if(!p)return;const cls='og-'+n.kind,r=n.kind==='book'?7:n.kind==='chapter'?5:8,label=String(n.label||''),short=label.length>15?label.slice(0,14)+'…':label;let tx=p[0]+12,anchor='start';if(n.kind==='author'){tx=p[0]-12;anchor='end'}out+=`<circle cx="${p[0]}" cy="${p[1]}" r="${r}" class="${cls}"><title>${escO(label)} · ${(+n.value||0).toLocaleString()}</title></circle><text x="${tx}" y="${p[1]+4}" text-anchor="${anchor}" class="og-label">${escO(short)}</text>`});svg.innerHTML=out}drawOntology();
const graph=OCG.claimGraph||{},claims=graph.claims||[],labels={supported:'已支持',partial:'有限定',unresolved:'待确认'},toolbar=document.getElementById('claimToolbar'),list=document.getElementById('claimList'),detail=document.getElementById('claimDetail');let filter='all',selected=claims[0]?.id||null;
function filtered(){return filter==='all'?claims:claims.filter(c=>c.status===filter)}
function drawToolbar(){if(!toolbar)return;const options=[['all','全部'],['supported','已支持'],['partial','有限定'],['unresolved','待确认']];toolbar.innerHTML=options.map(([k,l])=>`<button type="button" class="claim-filter ${filter===k?'active':''}" data-filter="${k}">${l} ${k==='all'?claims.length:(graph.statusCounts?.[k]||0)}</button>`).join('');toolbar.querySelectorAll('button').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;const rows=filtered();if(!rows.some(x=>x.id===selected))selected=rows[0]?.id||null;drawToolbar();drawClaims()})}
function evidenceRows(rows){return (rows||[]).length?(rows||[]).map(x=>`<div class="claim-evidence-item"><span>${escO(x.label)}</span><b>${escO(x.value)}</b></div>`).join(''):'<div class="claim-empty">无额外限定</div>'}
function drawDetail(claim){if(!detail)return;if(!claim){detail.innerHTML='<div class="claim-empty">当前筛选没有主张。</div>';return}detail.innerHTML=`<div class="claim-detail-kicker">${escO(claim.title)} · ${escO(claim.type)}</div><div class="claim-node"><span class="claim-status ${claim.status}">${labels[claim.status]||claim.status}</span><h3>${escO(claim.statement)}</h3></div><div class="claim-evidence-grid"><div class="claim-evidence-box"><h4>支持证据 SUPPORT</h4>${evidenceRows(claim.support)}</div><div class="claim-evidence-box"><h4>限定 / 反证 QUALIFIER</h4>${evidenceRows(claim.counter)}</div></div>${(claim.dependencies||[]).length?`<ul class="claim-deps">${claim.dependencies.map(x=>`<li>${escO(x)}</li>`).join('')}</ul>`:''}`}
function drawClaims(){const rows=filtered();if(list)list.innerHTML=rows.map(c=>`<button type="button" class="claim-row ${c.id===selected?'active':''}" data-id="${escO(c.id)}"><div class="claim-row-top"><b>${escO(c.title)}</b><span class="claim-status ${c.status}">${labels[c.status]||c.status}</span></div><small>${escO(c.statement)}</small></button>`).join('')||'<div class="claim-empty">当前筛选没有主张。</div>';list?.querySelectorAll('.claim-row').forEach(b=>b.onclick=()=>{selected=b.dataset.id;drawClaims()});drawDetail(rows.find(x=>x.id===selected)||rows[0])}
drawToolbar();drawClaims();
})();
'''


def augment(site_dir: Path = SITE, data_dir: Path = DATA) -> dict:
    index_path = site_dir / "index.html"
    report_path = site_dir / "report-data.json"
    if not index_path.exists() or not report_path.exists():
        raise SystemExit("ERROR: build Pages with pages_runtime.py first")
    report = load_json(report_path, {})
    include_private = str(report.get("privacyMode") or "") == "full"
    payload = build_payload(data_dir, include_private=include_private)
    report["ontologyClaims"] = payload
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    page = index_path.read_text(encoding="utf-8")
    if 'id="ontology-lite"' in page:
        print("Ontology/Claim Graph already present")
        return payload
    page = page.replace("</style>", CSS + "\n</style>", 1)
    page = page.replace("</nav>", '<a href="#ontology-lite">本体</a><a href="#claim-graph">证据主张</a></nav>', 1)
    marker = '  <article class="card half" id="blindspot">'
    if marker not in page:
        marker = '  <article class="card wide privacy">'
    page = page.replace(marker, HTML + "\n" + marker, 1)
    payload_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    js = JS_TEMPLATE.replace("__PAYLOAD__", payload_js)
    page = page.replace("</script>", js + "\n</script>", 1)
    index_path.write_text(page, encoding="utf-8")
    print(
        "Ontology Lite + Claim Graph: "
        f"{payload['ontology']['entityCounts']['Book']} books, "
        f"{payload['ontology']['entityCounts']['Chapter']} chapters, "
        f"{payload['claimGraph']['count']} claims"
    )
    return payload


if __name__ == "__main__":
    augment()
