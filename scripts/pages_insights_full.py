#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full-data deterministic insights for the GitHub Pages personal report.

This variant intentionally includes shelf entries marked ``secret=1`` because the
Pages deployment explicitly opts into full-data mode. Raw mark/review text is
still never emitted: only counts, dates, book metadata and relationships are
returned.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import build_pages_report as _report
import pages_enrichment
import pages_enrich_site
import pages_story_ui


def _env_true(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _install_enrichment_template() -> None:
    """Install ecosystem-derived UI into the existing report template."""
    if not _env_true("WEREAD_PAGES_INCLUDE_PRIVATE", False):
        return
    template = _report.TEMPLATE
    if 'id="shelf-explorer"' in template:
        return
    template = template.replace(
        "</style>",
        pages_enrich_site.CSS + "\n" + pages_story_ui.CSS + "\n</style>",
        1,
    )
    template = template.replace(
        "</nav>",
        '<a href="#career">生涯</a><a href="#clock">阅读时钟</a><a href="#progress">进度</a><a href="#recall">回顾</a><a href="#shelf-explorer">全书架</a></nav>',
        1,
    )
    marker = '  <article class="card wide privacy">'
    if marker in template:
        template = template.replace(
            marker,
            pages_story_ui.HTML + "\n" + pages_enrich_site.HTML + "\n" + marker,
            1,
        )
    template = template.replace(
        "</script>",
        "\nconst E=(D.insights||{}).enrichment||{};\n"
        + pages_enrich_site.JS
        + "\n"
        + pages_story_ui.JS
        + "\n</script>",
        1,
    )
    _report.TEMPLATE = template


_install_enrichment_template()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def bid(row: dict) -> str:
    return str(row.get("bookId") or (row.get("book") or {}).get("bookId") or "")


def author(row: dict) -> str:
    book = row.get("book") or row
    return str(book.get("author") or row.get("author") or "未知").strip() or "未知"


def category(row: dict) -> str:
    book = row.get("book") or row
    value = str(book.get("category") or row.get("category") or "").strip()
    if value:
        return value
    for item in book.get("categories") or []:
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            value = item.get("title") or item.get("category") or item.get("name")
            if value:
                return str(value).strip()
    return "未知"


def timestamp(raw):
    try:
        value = int(float(raw or 0))
        if not value:
            return None
        if value > 10_000_000_000:
            value //= 1000
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_insights(data_dir: Path) -> dict:
    shelf = load_json(data_dir / "weread_shelf.json", {})
    notebooks = load_json(data_dir / "weread_notebooks.json", [])
    notes = load_json(data_dir / "weread_notes_export.json", [])
    progress = load_json(data_dir / "weread_progress.json", {})
    info = load_json(data_dir / "weread_bookinfo.json", {})

    shelf_rows = list((shelf or {}).get("books") or [])
    shelf_by_id = {bid(x): x for x in shelf_rows if bid(x)}
    notebook_by_id = {bid(x): x for x in notebooks if bid(x)}
    notes_by_id = {bid(x): x for x in notes if bid(x)}
    ids = set(shelf_by_id) | set(notebook_by_id) | set(notes_by_id)

    yearly_category = defaultdict(Counter)
    yearly_author = defaultdict(Counter)
    yearly_kind = defaultdict(Counter)
    category_shelf = defaultdict(set)
    category_noted = defaultdict(set)
    category_notes = Counter()
    author_notes = Counter()
    author_categories = defaultdict(set)
    books = []
    marks_total = reviews_total = 0

    for book_id in sorted(ids):
        shelf_row = shelf_by_id.get(book_id) or {}
        notebook_row = notebook_by_id.get(book_id) or {}
        note_row = notes_by_id.get(book_id) or {}
        info_row = info.get(book_id) or {}
        source = shelf_row or notebook_row or note_row
        title = str(source.get("title") or (source.get("book") or {}).get("title") or note_row.get("title") or "未命名")
        a = author(source) if author(source) != "未知" else author(notebook_row)
        c = category(source)
        if c == "未知":
            c = str(info_row.get("category") or category(notebook_row) or "未知")
        marks = len(note_row.get("marks") or [])
        reviews = len(note_row.get("reviews") or [])
        n = marks + reviews
        marks_total += marks
        reviews_total += reviews
        if book_id in shelf_by_id:
            category_shelf[c].add(book_id)
        if n:
            category_noted[c].add(book_id)
            category_notes[c] += n
            author_notes[a] += n
            if a != "未知" and c != "未知":
                author_categories[a].add(c)

        first_note = last_note = None
        for kind, rows in (("mark", note_row.get("marks") or []), ("review", note_row.get("reviews") or [])):
            for item in rows:
                when = timestamp((item or {}).get("createTime"))
                if not when:
                    continue
                year = str(when.year)
                yearly_category[year][c] += 1
                yearly_author[year][a] += 1
                yearly_kind[year][kind] += 1
                first_note = when if first_note is None or when < first_note else first_note
                last_note = when if last_note is None or when > last_note else last_note

        books.append({
            "bookId": book_id,
            "title": title,
            "author": a,
            "category": c,
            "notes": n,
            "marks": marks,
            "reviews": reviews,
            "reviewRate": round(100 * reviews / n, 1) if n else 0.0,
            "progress": as_float((progress.get(book_id) or {}).get("progress")),
            "firstNote": first_note.date().isoformat() if first_note else None,
            "lastNote": last_note.date().isoformat() if last_note else None,
            "secret": int((shelf_row or {}).get("secret") or 0) == 1,
        })

    focus_shift = []
    previous = Counter()
    for year in sorted(yearly_category):
        current = yearly_category[year]
        total = sum(current.values())
        prev_total = sum(previous.values())

        def share(counter, key):
            s = sum(counter.values())
            return counter.get(key, 0) / s if s else 0.0

        top = []
        for c, count in current.most_common(5):
            now = share(current, c)
            before = share(previous, c) if prev_total else 0.0
            top.append({"category": c, "notes": count, "share": round(now * 100, 1), "delta": round((now-before)*100, 1) if prev_total else None})
        deltas = []
        for c in set(current) | set(previous):
            if c == "未知":
                continue
            deltas.append((share(current, c) - (share(previous, c) if prev_total else 0.0), c))
        rising = [{"category": c, "delta": round(d*100,1)} for d,c in sorted(deltas, reverse=True) if d > .03][:3]
        falling = [{"category": c, "delta": round(d*100,1)} for d,c in sorted(deltas) if d < -.03][:3]
        ta = next(((name,count) for name,count in yearly_author[year].most_common() if name != "未知"), ("—",0))
        rv = yearly_kind[year].get("review",0)
        mk = yearly_kind[year].get("mark",0)
        focus_shift.append({"year":year,"notes":total,"marks":mk,"reviews":rv,"reviewRate":round(100*rv/total,1) if total else 0.0,"topCategories":top,"rising":rising,"falling":falling,"topAuthor":{"author":ta[0],"notes":ta[1]}})
        previous = current

    invested = sorted((b for b in books if b["notes"] > 0), key=lambda x:(-x["notes"],x["title"]))
    top_cats = {c for c,_ in category_notes.most_common(7)}
    top_authors = {a for a,_ in author_notes.most_common(9) if a != "未知"}
    graph_books = [b for b in invested if b["category"] in top_cats and b["author"] in top_authors][:18]
    if len(graph_books) < 10:
        graph_books = invested[:18]
    nodes=[]; edges=[]; seen=set()

    def add(node_id,label,kind,value):
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append({"id":node_id,"label":label,"kind":kind,"value":value})

    for b in graph_books:
        ci=f"c:{b['category']}"; bi=f"b:{b['bookId']}"; ai=f"a:{b['author']}"
        add(ci,b["category"],"category",category_notes[b["category"]]); add(bi,b["title"],"book",b["notes"]); add(ai,b["author"],"author",author_notes[b["author"]])
        edges.append({"source":ci,"target":bi,"value":b["notes"]}); edges.append({"source":bi,"target":ai,"value":b["notes"]})
    bridges=[]
    for a,cats in author_categories.items():
        if a=="未知" or len(cats)<2:
            continue
        bridges.append({"author":a,"categories":sorted(cats),"categoryCount":len(cats),"notes":author_notes[a]})
    bridges.sort(key=lambda x:(-x["categoryCount"],-x["notes"],x["author"]))

    total_noted = sum(len(v) for v in category_noted.values())
    category_rows=[]
    for c in set(category_shelf)|set(category_noted):
        if c=="未知":
            continue
        s=len(category_shelf[c]); n=len(category_noted[c])
        category_rows.append({"category":c,"shelfBooks":s,"notedBooks":n,"notes":category_notes[c],"engagementRate":round(100*n/s,1) if s else None,"engagedShare":round(100*n/total_noted,1) if total_noted else 0.0})
    heavy=[x for x in category_rows if x["shelfBooks"]>=3 and x["engagementRate"] is not None and x["engagementRate"]<=25]
    heavy.sort(key=lambda x:(-x["shelfBooks"],x["engagementRate"],-x["notes"]))
    concentrated=sorted(category_rows,key=lambda x:(-x["engagedShare"],-x["notes"]))[:5]
    directions=[{"category":x["category"],"shelfBooks":x["shelfBooks"],"notedBooks":x["notedBooks"],"engagementRate":x["engagementRate"],"prompt":f"已收藏 {x['shelfBooks']} 本，但只有 {x['notedBooks']} 本形成笔记；可从现有书架任选一本做一次反向深读。"} for x in heavy[:6]]
    backlog=[]
    for b in books:
        if b["bookId"] not in shelf_by_id or b["notes"]>0:
            continue
        if b["progress"] is not None and b["progress"]>=10:
            continue
        backlog.append({"title":b["title"],"author":b["author"],"category":b["category"],"progress":b["progress"],"secret":b["secret"]})
    backlog.sort(key=lambda x:(x["category"],x["title"]))
    hhi=0.0
    if total_noted:
        for row in category_rows:
            share_value=row["notedBooks"]/total_noted
            hhi += share_value*share_value

    top_books=[{"bookId":b["bookId"],"title":b["title"],"author":b["author"],"category":b["category"],"notes":b["notes"],"marks":b["marks"],"reviews":b["reviews"],"reviewRate":b["reviewRate"],"progress":b["progress"],"firstNote":b["firstNote"],"lastNote":b["lastNote"],"secret":b["secret"]} for b in invested[:12]]
    total=marks_total+reviews_total
    result = {
        "version":"2-full",
        "scope":{"includePrivate":True,"secretBooks":sum(1 for x in shelf_rows if int(x.get("secret") or 0)==1),"rawTextPublished":False},
        "focusShift":focus_shift,
        "knowledgeGraph":{"nodes":nodes,"edges":edges,"bridgeAuthors":bridges[:8]},
        "blindspots":{"shelfHeavyLowEngagement":heavy[:8],"concentratedCategories":concentrated,"counterReadingDirections":directions,"lowProgressNoNoteBacklogCount":len(backlog),"lowProgressNoNoteBacklog":backlog[:10],"categoryConcentrationHHI":round(hhi,3)},
        "investment":{"topBooks":top_books,"marks":marks_total,"reviews":reviews_total,"reviewRate":round(100*reviews_total/total,1) if total else 0.0},
    }
    result["enrichment"] = pages_enrichment.build_enrichment(data_dir, include_private=True)
    return result
