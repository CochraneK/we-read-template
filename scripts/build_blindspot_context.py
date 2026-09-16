#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build deterministic evidence for blindspot/counter-reading analysis.

This script does not diagnose personality and does not recommend books. It only
computes concentration, engagement gaps, and stale-backlog facts that an AI
skill may interpret with explicit uncertainty.
"""
from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "blindspot_context.json"


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_context(context: dict) -> dict:
    books = [b for b in (context.get("books") or []) if isinstance(b, dict)]
    by_category = defaultdict(lambda: {
        "books": 0, "booksWithNotes": 0, "notes": 0,
        "knownProgress": 0, "progressSum": 0.0, "startedBooks": 0,
    })
    backlog = []

    for book in books:
        category = str(book.get("category") or "未知").strip() or "未知"
        row = by_category[category]
        row["books"] += 1
        note_count = int(book.get("noteCount") or 0)
        row["notes"] += note_count
        if note_count:
            row["booksWithNotes"] += 1

        progress = safe_float(book.get("progress"))
        if progress is not None:
            row["knownProgress"] += 1
            row["progressSum"] += progress
            if progress > 0:
                row["startedBooks"] += 1
        if (progress is None or progress < 10) and note_count == 0:
            backlog.append({
                "bookId": str(book.get("bookId") or ""),
                "title": str(book.get("title") or ""),
                "author": str(book.get("author") or ""),
                "category": category,
                "progress": progress,
            })

    category_rows = []
    total_engaged = sum(row["booksWithNotes"] for row in by_category.values())
    for category, row in by_category.items():
        books_count = row["books"]
        noted = row["booksWithNotes"]
        known = row["knownProgress"]
        category_rows.append({
            "category": category,
            "books": books_count,
            "booksWithNotes": noted,
            "engagementRate": round(noted / books_count, 4) if books_count else 0.0,
            "notes": row["notes"],
            "averageProgress": round(row["progressSum"] / known, 2) if known else None,
            "startedRate": round(row["startedBooks"] / known, 4) if known else None,
            "engagedShare": round(noted / total_engaged, 4) if total_engaged else 0.0,
        })
    category_rows.sort(key=lambda x: (-x["booksWithNotes"], -x["notes"], x["category"]))

    dominant = [x for x in category_rows if x["engagedShare"] >= 0.30]
    shelf_heavy = [
        x for x in category_rows
        if x["books"] >= 3 and x["engagementRate"] <= 0.25
    ]
    shelf_heavy.sort(key=lambda x: (-x["books"], x["engagementRate"]))
    backlog.sort(key=lambda x: (x["category"], x["title"]))

    return {
        "version": "1",
        "coverage": context.get("coverage") or {},
        "privacy": context.get("privacy") or {},
        "facts": {
            "categories": category_rows,
            "dominantCategories": dominant[:8],
            "shelfHeavyLowEngagementCategories": shelf_heavy[:12],
            "lowEngagementBacklog": backlog[:50],
            "lowEngagementBacklogCount": len(backlog),
        },
        "interpretationGuardrails": [
            "A concentration signal is not a flaw by itself; it may reflect intentional specialization.",
            "Shelf presence measures interest or acquisition, not completed reading.",
            "A low-engagement category may be new, aspirational, or metadata-noisy.",
            "Counter-reading directions should challenge claims and assumptions, not infer sensitive traits.",
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build deterministic WeRead blindspot evidence.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    result = build_context(context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    facts = result["facts"]
    print(
        f"blindspot-context: {args.output} | categories={len(facts['categories'])} "
        f"dominant={len(facts['dominantCategories'])} backlog={facts['lowEngagementBacklogCount']}"
    )


if __name__ == "__main__":
    main()
