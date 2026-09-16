#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a private evidence package for huashu's note-alchemy workflow.

Unlike public Pages contexts, this artifact intentionally contains raw marks and
user reviews. It must stay local/private. Deterministic code selects books,
separates source text from user-authored thoughts, groups evidence by chapter,
and decides whether a scope-confirmation gate is required before AI clustering.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "alchemy_context.json"


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())


def split_terms(topic: str, keywords: list[str] | None = None) -> list[str]:
    terms = []
    for value in [topic, *(keywords or [])]:
        for part in re.split(r"[,，、/|;；\s]+", str(value or "")):
            item = normalize(part)
            if item and item not in terms:
                terms.append(item)
    return terms


def match_topic(book: dict, terms: list[str]) -> bool:
    haystack = normalize(" ".join([
        str(book.get("title") or ""),
        str(book.get("author") or ""),
        str(book.get("category") or ""),
    ]))
    return bool(terms) and any(term in haystack for term in terms)


def select_single_book(books: list[dict], book_id: str = "", book_title: str = "") -> list[dict]:
    if book_id:
        matches = [b for b in books if str(b.get("bookId") or "") == str(book_id)]
        if not matches:
            raise ValueError(f"bookId not found: {book_id}")
        return matches
    needle = normalize(book_title)
    if not needle:
        raise ValueError("book_id or book_title is required for single-book mode")
    exact = [b for b in books if normalize(b.get("title") or "") == needle]
    if len(exact) == 1:
        return exact
    partial = [b for b in books if needle in normalize(b.get("title") or "")]
    if len(partial) == 1:
        return partial
    if not partial:
        raise ValueError(f"book title not found: {book_title}")
    raise ValueError("book title is ambiguous; use --book-id")


def evidence_rows(book: dict) -> list[dict]:
    rows = []
    for mark in book.get("marks") or []:
        if not isinstance(mark, dict):
            continue
        text = str(mark.get("text") or "").strip()
        if not text:
            continue
        rows.append({
            "type": "mark",
            "role": "source_text",
            "chapter": str(mark.get("chapter") or "未分章"),
            "text": text,
            "createTime": int(mark.get("createTime") or 0),
        })
    for review in book.get("reviews") or []:
        if not isinstance(review, dict):
            continue
        text = str(review.get("text") or "").strip()
        if not text:
            continue
        rows.append({
            "type": "review",
            "role": "user_thought",
            "chapter": str(review.get("chapter") or "未分章"),
            "abstract": str(review.get("abstract") or ""),
            "text": text,
            "createTime": int(review.get("createTime") or 0),
        })
    rows.sort(key=lambda r: (r["chapter"], r["createTime"], 0 if r["type"] == "mark" else 1))
    return rows


def package_book(book: dict) -> dict:
    evidence = evidence_rows(book)
    chapters = defaultdict(lambda: {"marks": [], "reviews": []})
    for row in evidence:
        target = "marks" if row["type"] == "mark" else "reviews"
        chapters[row["chapter"]][target].append(row)
    chapter_rows = []
    for chapter, group in chapters.items():
        chapter_rows.append({
            "chapter": chapter,
            "markCount": len(group["marks"]),
            "reviewCount": len(group["reviews"]),
            "marks": group["marks"],
            "reviews": group["reviews"],
        })
    chapter_rows.sort(key=lambda x: min(
        [r["createTime"] for r in x["marks"] + x["reviews"] if r["createTime"]] or [0]
    ))
    return {
        "bookId": str(book.get("bookId") or ""),
        "title": str(book.get("title") or ""),
        "author": str(book.get("author") or ""),
        "category": str(book.get("category") or ""),
        "markCount": sum(1 for r in evidence if r["type"] == "mark"),
        "reviewCount": sum(1 for r in evidence if r["type"] == "review"),
        "evidenceCount": len(evidence),
        "chapters": chapter_rows,
    }


def build_context(
    context: dict,
    *,
    book_id: str = "",
    book_title: str = "",
    topic: str = "",
    keywords: list[str] | None = None,
    gate_threshold: int = 50,
) -> dict:
    books = [b for b in (context.get("books") or []) if isinstance(b, dict)]
    if topic:
        mode = "topic"
        terms = split_terms(topic, keywords)
        selected = [b for b in books if match_topic(b, terms) and int(b.get("noteCount") or 0) > 0]
        selected.sort(key=lambda b: (-int(b.get("noteCount") or 0), str(b.get("title") or "")))
        selector = {"topic": topic, "terms": terms}
    else:
        mode = "book"
        selected = select_single_book(books, book_id=book_id, book_title=book_title)
        selector = {"bookId": str(selected[0].get("bookId") or ""), "title": str(selected[0].get("title") or "")}

    packaged = [package_book(book) for book in selected]
    total_marks = sum(b["markCount"] for b in packaged)
    total_reviews = sum(b["reviewCount"] for b in packaged)
    total_evidence = total_marks + total_reviews
    topic_book_count = len(packaged)

    if mode == "book":
        gate_required = False
        gate_reason = "Single-book mode does not require the cross-topic scope gate."
    else:
        gate_required = total_evidence > max(0, gate_threshold) or total_evidence > 500
        gate_reason = (
            f"Cross-topic evidence contains {total_evidence} items across {topic_book_count} books; choose subtopics before clustering."
            if gate_required
            else "Evidence volume is below the configured scope-gate threshold."
        )

    by_book = [
        {
            "bookId": b["bookId"],
            "title": b["title"],
            "author": b["author"],
            "category": b["category"],
            "marks": b["markCount"],
            "reviews": b["reviewCount"],
            "evidence": b["evidenceCount"],
        }
        for b in packaged
    ]

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "selector": selector,
        "privacy": {
            "containsRawEvidence": True,
            "publicPageSafe": False,
            "handling": "Keep local/private. Do not attach this payload to GitHub Pages or public report-data.json.",
            "sourcePolicy": context.get("privacy") or {},
        },
        "coverage": {
            "books": topic_book_count,
            "marks": total_marks,
            "reviews": total_reviews,
            "evidence": total_evidence,
        },
        "landscape": {
            "byBook": by_book,
            "requiresScopeConfirmation": gate_required,
            "scopeGateThreshold": gate_threshold,
            "scopeGateReason": gate_reason,
        },
        "books": packaged,
        "alchemyContract": {
            "readyForSynthesis": mode == "book" or not gate_required,
            "mustSeparateSourceAndUserThought": True,
            "sourceRole": "mark/source_text",
            "userRole": "review/user_thought",
            "singleBookNextSteps": [
                "derive 3-5 evidence-backed core claims",
                "compare author/source claims with user-authored reviews",
                "identify unresolved questions without inventing user beliefs",
            ],
            "topicNextSteps": [
                "if scope gate is required, present a coarse evidence landscape and let the user choose subtopics",
                "cluster by issue/theme rather than by book",
                "preserve source book attribution for every quoted/paraphrased evidence item",
                "end with unanswered questions grounded in evidence gaps",
            ],
        },
        "guardrails": [
            "Marks are source text and must never be presented as the user's own belief.",
            "Reviews are user-authored thought evidence; do not fabricate additional opinions.",
            "Do not dump all raw evidence as the final alchemy output.",
            "Avoid reproducing long continuous source passages; synthesize and quote sparingly.",
            "This artifact contains raw private reading evidence and must not be published on the public Page.",
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build a private evidence package for WeRead note alchemy.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--book-id", default="")
    group.add_argument("--book-title", default="")
    group.add_argument("--topic", default="")
    parser.add_argument("--keywords", default="", help="Comma-separated aliases for topic mode.")
    parser.add_argument("--gate-threshold", type=int, default=50)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}; run build_visualization_context.py first")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    keywords = [x.strip() for x in re.split(r"[,，、;；]+", args.keywords) if x.strip()]
    result = build_context(
        context,
        book_id=args.book_id,
        book_title=args.book_title,
        topic=args.topic,
        keywords=keywords,
        gate_threshold=max(0, args.gate_threshold),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"alchemy-context: {args.output} | mode={result['mode']} books={result['coverage']['books']} "
        f"evidence={result['coverage']['evidence']} gate={result['landscape']['requiresScopeConfirmation']} private=true"
    )


if __name__ == "__main__":
    main()
