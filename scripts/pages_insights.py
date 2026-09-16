#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic deep-insight layer for the public real-data GitHub Pages report.

This module deliberately avoids personality inference and raw-note publication.
It turns privacy-filtered WeRead data into auditable higher-order facts:
- year-over-year reading-focus shifts from note-event shares;
- a category -> book -> author knowledge network from actual note investment;
- shelf/engagement blindspots and counter-reading directions;
- top invested books and cross-category bridge authors.

Only aggregated counts, book metadata and category/author relationships are
returned. Raw highlight/review text never leaves this module.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pages_enrichment


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _book_id(item: dict) -> str:
    return str(item.get("bookId") or (item.get("book") or {}).get("bookId") or "")


def _author(item: dict) -> str:
    book = item.get("book") or item
    return str(book.get("author") or item.get("author") or "").strip()


def _category(item: dict) -> str:
    book = item.get("book") or item
    value = str(book.get("category") or item.get("category") or "").strip()
    if value:
        return value
    for raw in book.get("categories") or []:
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            candidate = raw.get("title") or raw.get("category") or raw.get("name")
            if candidate:
                return str(candidate).strip()
    return "未知"


def _as_int(value, default=0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_dt(raw):
    try:
        value = int(float(raw or 0))
        if not value:
            return None
        if value > 10_000_000_000:
            value //= 1000
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _note_counts(row: dict) -> tuple[int, int]:
    return len(row.get("marks") or []), len(row.get("reviews") or [])


def _metadata_for(bid: str, shelf_by_id: dict, notebook_by_id: dict, notes_by_id: dict, info: dict) -> dict:
    shelf = shelf_by_id.get(bid) or {}
    notebook = notebook_by_id.get(bid) or {}
    notes = notes_by_id.get(bid) or {}
    meta = info.get(bid) or {}
    source = shelf or notebook or notes
    return {
        "bookId": bid,
        "title": str(source.get("title") or (source.get("book") or {}).get("title") or notes.get("title") or "未命名"),
        "author": _author(source) or _author(notebook) or notes.get("author") or "未知",
        "category": _category(source) if _category(source) != "未知" else str(meta.get("category") or _category(notebook) or "未知"),
        "cover": str(source.get("cover") or (source.get("book") or {}).get("cover") or ""),
    }


def _share(counter: Counter, key: str) -> float:
    total = sum(counter.values())
    return (counter.get(key, 0) / total) if total else 0.0


def _round_share(value: float) -> float:
    return round(value * 100, 1)


def build_insights(data_dir: Path) -> dict:
    shelf = _load(data_dir / "weread_shelf.json", {})
    notebooks = _load(data_dir / "weread_notebooks.json", [])
    notes_export = _load(data_dir / "weread_notes_export.json", [])
    progress = _load(data_dir / "weread_progress.json", {})
    info = _load(data_dir / "weread_bookinfo.json", {})

    shelf_books = list((shelf or {}).get("books") or [])
    secret_ids = {
        _book_id(row)
        for row in shelf_books
        if _book_id(row) and _as_int(row.get("secret")) == 1
    }
    public_shelf = [row for row in shelf_books if _book_id(row) not in secret_ids]
    public_notebooks = [row for row in notebooks if _book_id(row) not in secret_ids]
    public_notes = [row for row in notes_export if _book_id(row) not in secret_ids]

    shelf_by_id = {_book_id(row): row for row in public_shelf if _book_id(row)}
    notebook_by_id = {_book_id(row): row for row in public_notebooks if _book_id(row)}
    notes_by_id = {_book_id(row): row for row in public_notes if _book_id(row)}
    all_ids = set(shelf_by_id) | set(notebook_by_id) | set(notes_by_id)

    books = []
    yearly_category = defaultdict(Counter)
    yearly_author = defaultdict(Counter)
    yearly_kind = defaultdict(Counter)
    category_books = defaultdict(set)
    category_noted_books = defaultdict(set)
    category_notes = Counter()
    author_notes = Counter()
    author_categories = defaultdict(set)
    total_marks = 0
    total_reviews = 0

    for bid in sorted(all_ids):
        meta = _metadata_for(bid, shelf_by_id, notebook_by_id, notes_by_id, info)
        notes_row = notes_by_id.get(bid) or {}
        marks, reviews = _note_counts(notes_row)
        total_marks += marks
        total_reviews += reviews
        note_total = marks + reviews
        category = meta["category"] or "未知"
        author = meta["author"] or "未知"
        progress_value = _as_float((progress.get(bid) or {}).get("progress"))
        if bid in shelf_by_id:
            category_books[category].add(bid)
        if note_total:
            category_noted_books[category].add(bid)
            category_notes[category] += note_total
            author_notes[author] += note_total
            if author != "未知" and category != "未知":
                author_categories[author].add(category)

        first_note = None
        last_note = None
        per_year = Counter()
        review_years = Counter()
        for kind, rows in (("mark", notes_row.get("marks") or []), ("review", notes_row.get("reviews") or [])):
            for item in rows:
                when = _to_dt((item or {}).get("createTime"))
                if not when:
                    continue
                year = str(when.year)
                per_year[year] += 1
                yearly_category[year][category] += 1
                yearly_author[year][author] += 1
                yearly_kind[year][kind] += 1
                if kind == "review":
                    review_years[year] += 1
                first_note = when if first_note is None or when < first_note else first_note
                last_note = when if last_note is None or when > last_note else last_note

        books.append({
            **meta,
            "noteCount": note_total,
            "markCount": marks,
            "reviewCount": reviews,
            "reviewRate": round(reviews / note_total, 4) if note_total else 0.0,
            "progress": progress_value,
            "firstNote": first_note.date().isoformat() if first_note else None,
            "lastNote": last_note.date().isoformat() if last_note else None,
            "years": dict(per_year),
            "reviewYears": dict(review_years),
        })

    # Year-over-year focus shifts from note-event share, not from absolute raw counts.
    focus_shift = []
    years = sorted(yearly_category)
    previous = Counter()
    for year in years:
        current = yearly_category[year]
        total = sum(current.values())
        previous_total = sum(previous.values())
        top_categories = []
        for category, count in current.most_common(5):
            current_share = _share(current, category)
            previous_share = _share(previous, category) if previous_total else 0.0
            top_categories.append({
                "category": category,
                "notes": count,
                "share": _round_share(current_share),
                "delta": round((current_share - previous_share) * 100, 1) if previous_total else None,
            })
        deltas = []
        keys = set(current) | set(previous)
        for category in keys:
            if category == "未知":
                continue
            delta = _share(current, category) - (_share(previous, category) if previous_total else 0.0)
            deltas.append((delta, category))
        rising = [
            {"category": category, "delta": round(delta * 100, 1)}
            for delta, category in sorted(deltas, reverse=True)
            if delta > 0.03
        ][:3]
        falling = [
            {"category": category, "delta": round(delta * 100, 1)}
            for delta, category in sorted(deltas)
            if delta < -0.03
        ][:3]
        top_author = next(((a, n) for a, n in yearly_author[year].most_common() if a != "未知"), ("—", 0))
        marks = yearly_kind[year].get("mark", 0)
        reviews = yearly_kind[year].get("review", 0)
        focus_shift.append({
            "year": year,
            "notes": total,
            "marks": marks,
            "reviews": reviews,
            "reviewRate": round(100 * reviews / total, 1) if total else 0.0,
            "topCategories": top_categories,
            "rising": rising,
            "falling": falling,
            "topAuthor": {"author": top_author[0], "notes": top_author[1]},
        })
        previous = current

    # Knowledge network: top categories -> top invested books -> authors.
    invested_books = [book for book in books if book["noteCount"] > 0]
    invested_books.sort(key=lambda x: (-x["noteCount"], x["title"]))
    top_books = invested_books[:16]
    top_categories = {name for name, _ in category_notes.most_common(7)}
    top_authors = {name for name, _ in author_notes.most_common(9) if name != "未知"}
    network_books = [
        book for book in invested_books
        if book["category"] in top_categories and book["author"] in top_authors
    ][:18]
    if len(network_books) < 10:
        network_books = top_books[:18]

    network_nodes = []
    network_edges = []
    seen_nodes = set()

    def add_node(node_id: str, label: str, kind: str, value: int):
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        network_nodes.append({"id": node_id, "label": label, "kind": kind, "value": value})

    for book in network_books:
        bid = book["bookId"]
        cat = book["category"] or "未知"
        author = book["author"] or "未知"
        cat_id = f"c:{cat}"
        book_node_id = f"b:{bid}"
        author_id = f"a:{author}"
        add_node(cat_id, cat, "category", category_notes.get(cat, 0))
        add_node(book_node_id, book["title"], "book", book["noteCount"])
        add_node(author_id, author, "author", author_notes.get(author, 0))
        network_edges.append({"source": cat_id, "target": book_node_id, "value": book["noteCount"]})
        network_edges.append({"source": book_node_id, "target": author_id, "value": book["noteCount"]})

    bridge_authors = []
    for author, categories in author_categories.items():
        if author == "未知" or len(categories) < 2:
            continue
        bridge_authors.append({
            "author": author,
            "categories": sorted(categories),
            "categoryCount": len(categories),
            "notes": author_notes[author],
        })
    bridge_authors.sort(key=lambda x: (-x["categoryCount"], -x["notes"], x["author"]))

    # Blindspot evidence: shelf presence vs actual notebook investment.
    blindspot_rows = []
    all_categories = set(category_books) | set(category_noted_books)
    total_noted_books = sum(len(v) for v in category_noted_books.values())
    for category in all_categories:
        if category == "未知":
            continue
        shelf_count = len(category_books[category])
        noted_count = len(category_noted_books[category])
        notes_count = category_notes[category]
        blindspot_rows.append({
            "category": category,
            "shelfBooks": shelf_count,
            "notedBooks": noted_count,
            "notes": notes_count,
            "engagementRate": round(100 * noted_count / shelf_count, 1) if shelf_count else None,
            "engagedShare": round(100 * noted_count / total_noted_books, 1) if total_noted_books else 0.0,
        })

    shelf_heavy = [
        row for row in blindspot_rows
        if row["shelfBooks"] >= 3 and (row["engagementRate"] is not None and row["engagementRate"] <= 25)
    ]
    shelf_heavy.sort(key=lambda x: (-x["shelfBooks"], x["engagementRate"], -x["notes"]))

    concentrated = sorted(blindspot_rows, key=lambda x: (-x["engagedShare"], -x["notes"]))[:5]
    counter_directions = []
    for row in shelf_heavy[:6]:
        counter_directions.append({
            "category": row["category"],
            "shelfBooks": row["shelfBooks"],
            "notedBooks": row["notedBooks"],
            "engagementRate": row["engagementRate"],
            "prompt": f"已收藏 {row['shelfBooks']} 本，但只有 {row['notedBooks']} 本形成笔记；可从现有书架任选一本做一次反向深读。",
        })

    # Low-progress, no-note backlog from known progress data. Titles only, no raw text.
    backlog = []
    for book in books:
        progress_value = book["progress"]
        if book["bookId"] not in shelf_by_id or book["noteCount"] > 0:
            continue
        if progress_value is not None and progress_value >= 10:
            continue
        backlog.append({
            "title": book["title"],
            "author": book["author"],
            "category": book["category"],
            "progress": progress_value,
        })
    backlog.sort(key=lambda x: (x["category"], x["title"]))

    top_invested_books = []
    for book in top_books[:12]:
        top_invested_books.append({
            "bookId": book["bookId"],
            "title": book["title"],
            "author": book["author"],
            "category": book["category"],
            "notes": book["noteCount"],
            "marks": book["markCount"],
            "reviews": book["reviewCount"],
            "reviewRate": round(book["reviewRate"] * 100, 1),
            "progress": book["progress"],
            "firstNote": book["firstNote"],
            "lastNote": book["lastNote"],
        })

    total_notes = total_marks + total_reviews
    concentration_hhi = 0.0
    if total_noted_books:
        for row in blindspot_rows:
            share = (row["notedBooks"] / total_noted_books) if total_noted_books else 0
            concentration_hhi += share * share

    result = {
        "version": "2-filtered",
        "scope": {
            "includePrivate": False,
            "secretBooks": len(secret_ids),
            "rawTextPublished": False,
        },
        "privacy": {
            "privateExcluded": len(secret_ids),
            "rawTextPublished": False,
            "policy": "explicit secret=1 books excluded; raw mark/review text never emitted",
        },
        "focusShift": focus_shift,
        "knowledgeGraph": {
            "nodes": network_nodes,
            "edges": network_edges,
            "bridgeAuthors": bridge_authors[:8],
        },
        "blindspots": {
            "shelfHeavyLowEngagement": shelf_heavy[:8],
            "concentratedCategories": concentrated,
            "counterReadingDirections": counter_directions,
            "lowProgressNoNoteBacklogCount": len(backlog),
            "lowProgressNoNoteBacklog": backlog[:10],
            "categoryConcentrationHHI": round(concentration_hhi, 3),
        },
        "investment": {
            "topBooks": top_invested_books,
            "marks": total_marks,
            "reviews": total_reviews,
            "reviewRate": round(100 * total_reviews / total_notes, 1) if total_notes else 0.0,
        },
    }
    result["enrichment"] = pages_enrichment.build_enrichment(data_dir, include_private=False)
    return result


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parents[1]
    result = build_insights(ROOT / "data")
    print(json.dumps({
        "focusYears": len(result["focusShift"]),
        "knowledgeNodes": len(result["knowledgeGraph"]["nodes"]),
        "knowledgeEdges": len(result["knowledgeGraph"]["edges"]),
        "counterDirections": len(result["blindspots"]["counterReadingDirections"]),
        "topBooks": len(result["investment"]["topBooks"]),
    }, ensure_ascii=False))
