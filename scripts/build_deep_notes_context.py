#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build private deterministic deep-note analysis from visualization_context.json.

This modernizes the useful C/D note-analysis ideas from the legacy dashboard
without inheriting its monolithic renderer, privacy leakage, or category-counting
bugs. Raw duplicate text samples make this artifact private-only.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "private_lab" / "deep_notes_context.json"

LENGTH_BUCKETS = (
    ("1-20", 1, 20),
    ("21-40", 21, 40),
    ("41-80", 41, 80),
    ("81-160", 81, 160),
    ("161+", 161, None),
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def length_bucket(length: int) -> str:
    for label, low, high in LENGTH_BUCKETS:
        if length >= low and (high is None or length <= high):
            return label
    return "0"


def evidence_chapter(item: dict) -> str:
    return str(item.get("chapter") or "未标章节").strip() or "未标章节"


def build_context(context: dict) -> dict:
    books = [b for b in (context.get("books") or []) if isinstance(b, dict)]
    length_counts = Counter()
    duplicate_map = defaultdict(list)
    position_deciles = Counter()
    interplay_totals = Counter()
    per_book = []

    for book in books:
        marks = [m for m in (book.get("marks") or []) if isinstance(m, dict)]
        reviews = [r for r in (book.get("reviews") or []) if isinstance(r, dict)]
        mark_chapters = [evidence_chapter(m) for m in marks]
        review_chapters = [evidence_chapter(r) for r in reviews]
        mark_set, review_set = set(mark_chapters), set(review_chapters)
        both = mark_set & review_set
        only_mark = mark_set - review_set
        only_review = review_set - mark_set
        interplay_totals["both"] += len(both)
        interplay_totals["onlyMark"] += len(only_mark)
        interplay_totals["onlyReview"] += len(only_review)

        chapter_order = list(dict.fromkeys(mark_chapters))
        chapter_index = {chapter: i for i, chapter in enumerate(chapter_order)}
        if len(chapter_order) >= 2:
            denominator = len(chapter_order) - 1
            for chapter in mark_chapters:
                pos = chapter_index[chapter] / denominator
                decile = min(10, int(pos * 10) + 1)
                position_deciles[decile] += 1

        for mark in marks:
            text = str(mark.get("text") or "").strip()
            if not text:
                continue
            length_counts[length_bucket(len(text))] += 1
            norm = normalize_text(text)
            if len(norm) >= 6:
                duplicate_map[norm].append({
                    "bookId": str(book.get("bookId") or ""),
                    "title": str(book.get("title") or ""),
                    "chapter": evidence_chapter(mark),
                    "text": text,
                })

        total = len(marks) + len(reviews)
        per_book.append({
            "bookId": str(book.get("bookId") or ""),
            "title": str(book.get("title") or ""),
            "author": str(book.get("author") or ""),
            "category": str(book.get("category") or ""),
            "marks": len(marks),
            "reviews": len(reviews),
            "notes": total,
            "reviewShare": round(len(reviews) / total, 4) if total else 0.0,
            "chapterInterplay": {
                "both": len(both),
                "onlyMark": len(only_mark),
                "onlyReview": len(only_review),
            },
        })

    duplicates = []
    for occurrences in duplicate_map.values():
        if len(occurrences) < 2:
            continue
        first = occurrences[0]
        duplicates.append({
            "text": first["text"],
            "count": len(occurrences),
            "books": [
                {"bookId": row["bookId"], "title": row["title"], "chapter": row["chapter"]}
                for row in occurrences[:12]
            ],
        })
    duplicates.sort(key=lambda x: (-x["count"], -len(x["text"]), x["text"]))

    thought_rich = sorted(
        [row for row in per_book if row["reviews"] > 0],
        key=lambda x: (-x["reviews"], -x["reviewShare"], -x["notes"], x["title"]),
    )[:30]
    highlight_heavy = sorted(
        [row for row in per_book if row["marks"] > 0],
        key=lambda x: (-x["marks"], x["reviewShare"], -x["notes"], x["title"]),
    )[:30]

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "publicPageSafe": False,
            "containsRawEvidence": bool(duplicates),
            "sourcePolicy": context.get("privacy") or {},
            "note": "Duplicate highlight samples may contain copyrighted/source text; keep this artifact local/private.",
        },
        "coverage": {
            "books": len(books),
            "booksWithNotes": sum(1 for row in per_book if row["notes"] > 0),
            "marks": sum(row["marks"] for row in per_book),
            "reviews": sum(row["reviews"] for row in per_book),
        },
        "highlightLength": {
            "buckets": [{"label": label, "count": length_counts.get(label, 0)} for label, _, _ in LENGTH_BUCKETS],
        },
        "chapterPosition": {
            "deciles": [{"decile": i, "count": position_deciles.get(i, 0)} for i in range(1, 11)],
            "method": "Within each book, chapter order is approximated by first appearance among saved marks; this is not a canonical table-of-contents position.",
        },
        "markReviewInterplay": {
            "both": interplay_totals["both"],
            "onlyMark": interplay_totals["onlyMark"],
            "onlyReview": interplay_totals["onlyReview"],
            "meaning": "Chapter-level evidence topology only; it does not imply agreement, comprehension, or personality.",
        },
        "duplicateHighlights": duplicates[:100],
        "duplicateHighlightCount": len(duplicates),
        "thoughtRichBooks": thought_rich,
        "highlightHeavyBooks": highlight_heavy,
        "books": per_book,
        "guardrails": [
            "A saved highlight is source text, not automatically the user's belief.",
            "A review is user-authored evidence but still should not be over-generalized into personality claims.",
            "Duplicate highlights can arise from repeated editions/imports and are a review signal, not proof of importance.",
            "Chapter-position analysis is approximate unless canonical chapter order is enriched separately.",
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build private deterministic deep-note analysis.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}; run build_visualization_context.py first")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    result = build_context(context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    c = result["coverage"]
    print(
        f"deep-notes-context: {args.output} | books={c['booksWithNotes']} marks={c['marks']} "
        f"reviews={c['reviews']} duplicate_highlights={result['duplicateHighlightCount']} private=true"
    )


if __name__ == "__main__":
    main()
