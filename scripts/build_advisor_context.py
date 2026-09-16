#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build deterministic facts for evidence-backed reading advice.

This is the factual first stage of the huashu advisor/path workflows. It does
not recommend books and does not infer personality. It classifies reading depth,
shelf-vs-notebook gaps, recent activity, and category engagement so a later
advisor can reason from an explicit evidence package.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "advisor_context.json"


def as_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _book_fact(book: dict) -> dict:
    progress = as_float(book.get("progress"))
    return {
        "bookId": str(book.get("bookId") or ""),
        "title": str(book.get("title") or ""),
        "author": str(book.get("author") or ""),
        "category": str(book.get("category") or "未知").strip() or "未知",
        "noteCount": as_int(book.get("noteCount")),
        "markCount": as_int(book.get("markCount")),
        "reviewCount": as_int(book.get("reviewCount")),
        "progress": progress,
        "updateTime": as_int(book.get("shelfReadUpdateTime") or book.get("updateTime")),
        "inShelf": bool(book.get("inShelf", book.get("privacyKnown", False))),
        "inNotebook": bool(book.get("inNotebook", as_int(book.get("noteCount")) > 0)),
    }


def _depth_label(note_count: int) -> str:
    # Mirrors huashu/shared/knowledge-map.md while keeping the bands exclusive.
    if note_count >= 20:
        return "deep"
    if note_count >= 10:
        return "medium"
    if note_count >= 3:
        return "light"
    if note_count >= 1:
        return "glance"
    return "none"


def build_context(context: dict, *, as_of: int | None = None) -> dict:
    books = [_book_fact(b) for b in (context.get("books") or []) if isinstance(b, dict)]
    now_ts = as_int(as_of) if as_of is not None else int(datetime.now(timezone.utc).timestamp())

    bands = {"deep": [], "medium": [], "light": [], "glance": [], "none": []}
    hidden_deep = []
    shelved_unengaged = []
    categories = defaultdict(lambda: {
        "shelfBooks": 0,
        "notebookBooks": 0,
        "notes": 0,
        "deepBooks": 0,
        "mediumBooks": 0,
        "recent7d": 0,
        "recent30d": 0,
    })

    for book in books:
        label = _depth_label(book["noteCount"])
        bands[label].append(book)
        if not book["inShelf"] and book["noteCount"] >= 10:
            hidden_deep.append(book)
        if book["inShelf"] and book["noteCount"] == 0:
            shelved_unengaged.append(book)

        row = categories[book["category"]]
        if book["inShelf"]:
            row["shelfBooks"] += 1
        if book["inNotebook"] or book["noteCount"] > 0:
            row["notebookBooks"] += 1
        row["notes"] += book["noteCount"]
        if label == "deep":
            row["deepBooks"] += 1
        elif label == "medium":
            row["mediumBooks"] += 1

        age = now_ts - book["updateTime"] if book["updateTime"] else None
        if age is not None and 0 <= age <= 7 * 86400:
            row["recent7d"] += 1
        if age is not None and 0 <= age <= 30 * 86400:
            row["recent30d"] += 1

    for rows in bands.values():
        rows.sort(key=lambda b: (-b["noteCount"], -b["updateTime"], b["title"]))
    hidden_deep.sort(key=lambda b: (-b["noteCount"], b["title"]))
    shelved_unengaged.sort(key=lambda b: (-b["updateTime"], b["title"]))

    category_rows = []
    for category, row in categories.items():
        shelf_count = row["shelfBooks"]
        notebook_count = row["notebookBooks"]
        category_rows.append({
            "category": category,
            **row,
            "engagementRate": round(notebook_count / shelf_count, 4) if shelf_count else None,
        })
    category_rows.sort(key=lambda r: (-r["notes"], -r["notebookBooks"], r["category"]))

    recent = [b for b in books if b["updateTime"] > 0]
    recent.sort(key=lambda b: (-b["updateTime"], -b["noteCount"], b["title"]))
    recent7 = [b for b in recent if 0 <= now_ts - b["updateTime"] <= 7 * 86400]
    recent30 = [b for b in recent if 0 <= now_ts - b["updateTime"] <= 30 * 86400]

    deep_categories = [r for r in category_rows if r["deepBooks"] + r["mediumBooks"] > 0]
    shelf_heavy = [
        r for r in category_rows
        if r["shelfBooks"] >= 3 and (r["engagementRate"] is not None and r["engagementRate"] <= 0.25)
    ]
    shelf_heavy.sort(key=lambda r: (-r["shelfBooks"], r["engagementRate"], r["category"]))

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "asOf": now_ts,
        "privacy": context.get("privacy") or {},
        "coverage": context.get("coverage") or {},
        "facts": {
            "depthBands": {
                "deep20Plus": bands["deep"],
                "medium10To19": bands["medium"],
                "light3To9": bands["light"],
                "glance1To2": bands["glance"],
                "noNotes": bands["none"],
            },
            "hiddenDeepBooks": hidden_deep,
            "shelvedUnengagedBooks": shelved_unengaged,
            "recent7d": recent7[:30],
            "recent30d": recent30[:60],
            "recentBooks": recent[:30],
            "categories": category_rows,
            "deepCategories": deep_categories[:12],
            "shelfHeavyLowEngagementCategories": shelf_heavy[:12],
        },
        "advisorContract": {
            "readyForRecommendation": False,
            "nextRequiredStep": "Choose a topic or infer a candidate topic from recent/deep evidence, then enrich knowledge-gap axes and verify every recommendation against the current WeRead catalog.",
            "gapAxesRequiringEnrichment": [
                "school_or_viewpoint",
                "era_or_paradigm",
                "abstraction_level",
                "adjacent_discipline",
            ],
            "mustVerifyAvailability": True,
            "mustExcludeAlreadyRead": True,
            "mustExplainEvidence": True,
        },
        "guardrails": [
            "Shelf presence is interest/acquisition evidence, not proof of reading.",
            "One or two notes are weak evidence and should not define an interest area.",
            "Recent activity is a secondary signal when the user explicitly names a topic.",
            "This context must not itself recommend books or infer sensitive/personality traits.",
            "Knowledge-gap axes require book/content enrichment; category metadata alone cannot establish schools, paradigms, or missing disciplines.",
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build deterministic WeRead advisor evidence.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of", type=int, default=None, help="Unix timestamp for deterministic testing/replays.")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}")
    source = json.loads(args.context.read_text(encoding="utf-8"))
    result = build_context(source, as_of=args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    facts = result["facts"]
    print(
        f"advisor-context: {args.output} | deep={len(facts['depthBands']['deep20Plus'])} "
        f"hidden_deep={len(facts['hiddenDeepBooks'])} recent30d={len(facts['recent30d'])}"
    )


if __name__ == "__main__":
    main()
